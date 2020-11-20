#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains the ``DomainReview`` class. The class checks if a domain name is
properly categorized, has not been flagged in VirusTotal, or tagged with a bad category.

``DomainReview`` checks VirusTotal and malwaredomains.com's list of reported domains.
"""

# Standard Libraries
from time import sleep
import traceback
import logging

# Django & Other 3rd Party Libraries
import requests

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import VirusTotalConfiguration

# Disable requests warnings for things like disabling certificate checking
requests.packages.urllib3.disable_warnings()

# Using __name__ resolves to ghostwriter.modules.review
logger = logging.getLogger(__name__)


class DomainReview(object):
    """
    Pull a list of domain names and check their web reputation.
    """

    # Get API configuration
    virustotal_config = VirusTotalConfiguration.get_solo()
    if virustotal_config.enable is False:
        logger.error(
            "Tried to run a domain review without VirusTotal configured and enabled"
        )
        exit()
    sleep_time = virustotal_config.sleep_time

    # API endpoints
    malwaredomains_url = "http://mirror1.malwaredomains.com/files/justdomains"
    virustotal_domain_report_uri = "https://www.virustotal.com/vtapi/v2/domain/report?apikey={api_key}&domain={domain}"

    # Categories we don't want to see
    # These are lowercase to avoid inconsistencies with how each service might return the categories
    blocklist = [
        "phishing",
        "web ads/analytics",
        "suspicious",
        "placeholders",
        "pornography",
        "spam",
        "gambling",
        "scam/questionable/illegal",
        "malicious sources/malnets",
    ]
    # Variables for web browsing
    useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    session = requests.Session()

    def __init__(self, domain_queryset, sleep_time_override):
        self.domain_queryset = domain_queryset

        # Override globally configured sleep time
        if sleep_time_override:
            self.sleep_time = sleep_time_override

    def check_virustotal(self, domain, ignore_case=False):
        """
        Look-up the provided domain name in VirusTotal.

        **Parameters**

        ``domain``
            Domain name to search
        ``ignore_case``
            Do not convert domain name to lowercase (Default: False)
        """
        results = {}
        results["result"] = "success"
        if self.virustotal_config.enable:
            # The VT API is case sensitive, so domains should always be lowercase
            if not ignore_case:
                domain = domain.lower()
            try:
                req = self.session.get(
                    self.virustotal_domain_report_uri.format(
                        api_key=self.virustotal_config.api_key, domain=domain
                    )
                )
                if req.ok:
                    vt_data = req.json()
                    results["data"] = vt_data
                else:
                    results["result"] = "error"
                    results["error"] = "VirusTotal rejected the API key in settings"
            except Exception:
                trace = traceback.format_exc()
                logger.exception("Failed to contact VirusTotal")
                results["result"] = "error"
                results["error"] = "{exception}".format(exception=trace)
        else:
            results["result"] = "error"
            results["error"] = "VirusTotal is disabled in settings"

        return results

    def download_malware_domains(self):
        """
        Download the malwaredomains.com list of malicious domains.
        """
        results = {}
        results["result"] = "success"
        headers = {"User-Agent": self.useragent}
        response = self.session.get(
            url=self.malwaredomains_url, headers=headers, verify=False
        )
        malware_domains = response.text
        if response.status_code == 200:
            results["malware_domains"] = malware_domains
            logger.info(
                "Successfully collected list of %s domains from malwaredomains.com",
                len(results["malware_domains"]),
            )
            return results
        else:
            results["result"] = "error"
            results["error"] = "Received status code {status_code}".format(
                status_code=response.status_code
            )
            logger.error(
                "Failed to fetch the malwaredomains.com list from %s with status code: %s",
                self.malwaredomains_url,
                response.status_code,
            )
            return results

    def check_domain_status(self):
        """
        Check the status of each domain name in the provided :model:`shepherd.Domain`
        queryset. Mark the domain as burned if a vendor has flagged it for malware or
        phishing or assigned it an undesirable category.
        """
        lab_results = {}
        malware_domains = self.download_malware_domains()
        for domain in self.domain_queryset:
            burned = False
            if domain.is_expired() is False:
                domain_categories = []
                burned_explanations = []
                lab_results[domain] = {}
                logger.info("Starting domain category update for %s", domain.name)

                # Sort the domain information from queryset
                domain_name = domain.name
                health = domain.health_status
                logger.info("Domain is currently considered to be %s", health)

                # Check if domain is flagged for malware
                if malware_domains["result"] == "success":
                    if domain_name in malware_domains["malware_domains"]:
                        logger.warning(
                            "The domain %s is listed as a known malicious domain",
                            domain_name,
                        )
                        burned = True
                        burned_explanations.append(
                            f"<p>Flagged for malware by <em>malwaredomains.com</em>. See {self.malwaredomains_url} for the list.</p>"
                        )

                # Check domain name with VirusTotal
                vt_results = self.check_virustotal(domain_name)
                if vt_results["result"] == "success":
                    logger.info("Received results for %s from VirusTotal", domain_name)
                    lab_results[domain]["vt_results"] = vt_results["data"]

                    # Locate category data
                    if "categories" in vt_results["data"]:
                        domain_categories = vt_results["data"]["categories"]
                    search_key = "category"
                    more_categories = [
                        val
                        for key, val in vt_results["data"].items()
                        if search_key in key
                    ]
                    domain_categories.extend(more_categories)

                    # Make categories unique
                    domain_categories = list(set(domain_categories))

                    # Check if VirusTotal has any detections for URLs or malware samples
                    if "detected_downloaded_samples" in vt_results["data"]:
                        if len(vt_results["data"]["detected_downloaded_samples"]) > 0:
                            total_detections = len(vt_results["data"]["detected_downloaded_samples"])
                            logger.warning(
                                "Domain %s is tied to {total_detections} VirusTotal malware sample(s)",
                                domain_name,
                            )
                            burned = True
                            burned_explanations.append(
                                f"<p>Tied to {total_detections} VirusTotal malware sample(s):</p>"
                            )
                            for detection in vt_results["data"]["detected_downloaded_samples"]:
                                burned_explanations.append(
                                    f"<p>SHA256 hash {detection['sha256']} flagged by {detection['positives']} vendors on {detection['date']}</p>"
                                )
                    if "detected_urls" in vt_results["data"]:
                        if len(vt_results["data"]["detected_urls"]) > 0:
                            total_detections = len(vt_results["data"]["detected_urls"])
                            logger.warning(
                                "Domain %s has a positive malware detection on VirusTotal.",
                                domain_name,
                            )
                            burned = True
                            burned_explanations.append(
                                f"<p>Domain has {total_detections} malware detections on VirusTotal:</p>"
                            )
                            for detection in vt_results["data"]["detected_urls"]:
                                burned_explanations.append(
                                    f"<p>{detection['url']} flagged by {detection['positives']} vendors on {detection['scan_date']}</p>"
                                )
                else:
                    lab_results[domain]["vt_results"] = "none"
                    logger.warning(
                        "Did not receive results for %s from VirusTotal", domain_name
                    )

                # Check if any categories are suspect
                bad_categories = []
                for category in domain_categories:
                    if category.lower() in self.blocklist:
                        bad_categories.append(category)
                if bad_categories:
                    logger.warning(
                        "Domain %s is now burned because of undesirable categories: %s",
                        domain_name,
                        bad_categories,
                    )
                    burned = True
                    burned_explanations.append(
                        "<p>Tagged with one or more undesirable categories: {bad_cat}</p>".format(
                            bad_cat=", ".join(bad_categories)
                        )
                    )

                # Assemble the dictionary to return for this domain
                lab_results[domain]["burned"] = burned
                lab_results[domain]["categories"] = domain_categories
                if burned:
                    lab_results[domain]["burned_explanation"] = burned_explanations

                # Sleep for a while for VirusTotal's API
                sleep(self.sleep_time)
            else:
                logger.warning(
                    "Domain %s is expired, so skipped it",
                    domain.name,
                )
        return lab_results
