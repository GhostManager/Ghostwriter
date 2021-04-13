#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains the ``DomainReview`` class. The class checks if a domain name is
properly categorized, has not been flagged in VirusTotal, or tagged with a bad category.
"""

# Standard Libraries
import datetime
from time import sleep
import traceback
import logging


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

    **Parameters**

    ``domain_queryset``
        Queryset for :model:`shepherd:Domain`
    ``sleep_time_override``
        Number of seconds to sleep betwen VirusTotal API requests
        (overrides global configuration)
    """

    # API endpoints
    VIRUSTOTAL_BASE_API_URI = "https://www.virustotal.com/vtapi/v2"

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
    session = requests.Session()

    def __init__(self, domain_queryset, sleep_time_override=None):
        # Get API configuration
        self.virustotal_config = VirusTotalConfiguration.get_solo()
        if self.virustotal_config.enable is False:
            logger.error(
                "Tried to start a domain review without VirusTotal configured and enabled"
            )
            exit()

        # Override globally configured sleep time
        if sleep_time_override:
            self.sleep_time = sleep_time_override
        else:
            self.sleep_time = self.virustotal_config.sleep_time

        self.domain_queryset = domain_queryset

    def get_domain_report(self, domain, ignore_case=False):
        """
        Look-up the provided domain name with VirusTotal's Domain Report API endpoint.

        # Ref: https://developers.virustotal.com/reference#domain-report

        **Parameters**

        ``domain``
            Domain name to search
        ``ignore_case``
            Do not convert domain name to lowercase (Default: False)
        """
        virustotal_domain_report_uri = "/domain/report"
        url = self.VIRUSTOTAL_BASE_API_URI + virustotal_domain_report_uri
        results = {}
        results["result"] = "success"
        if self.virustotal_config.enable:
            # The VT API is case sensitive, so domains should always be lowercase
            if not ignore_case:
                domain = domain.lower()
            try:
                params = {
                    "apikey": self.virustotal_config.api_key,
                    "domain": domain,
                }
                req = self.session.get(url, params=params)
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

    def get_url_report(self, resource, allinfo=True, ignore_case=False):
        """
        Look-up the provided domain name with VirusTotal's URL Report API endpoint.

        Ref: https://developers.virustotal.com/reference#url-report

        **Parameters**

        ``resource``
            URL for which you want to retrieve the most recent report
        ``allinfo``
            Return additional information available from VirusTotal–see reference (Default: True)
        ``ignore_case``
            Do not convert domain name to lowercase (Default: False)
        """
        virustotal_url_report_uri = "/url/report"
        url = self.VIRUSTOTAL_BASE_API_URI + virustotal_url_report_uri
        results = {}
        results["result"] = "success"
        if self.virustotal_config.enable:
            # The VT API is case sensitive, so domains should always be lowercase
            if not ignore_case:
                resource = resource.lower()
            try:
                params = {
                    "apikey": self.virustotal_config.api_key,
                    "resource": resource,
                    "allinfo": allinfo,
                }
                req = self.session.get(url, params=params)
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

    def check_domain_status(self):
        """
        Check the status of each domain name in the provided :model:`shepherd.Domain`
        queryset. Mark the domain as burned if a vendor has flagged it for malware or
        phishing or assigned it an undesirable category.
        """
        lab_results = {}
        for domain in self.domain_queryset:
            burned = False
            # Ignore any expired domains because we don't control them anymore
            if domain.is_expired() is False:
                domain_categories = []
                burned_explanations = []
                lab_results[domain] = {}
                warnings = []
                lab_results[domain]["warnings"] = {}
                logger.info("Starting domain category update for %s", domain.name)

                # Sort the domain information from queryset
                domain_name = domain.name
                health = domain.health_status

                # For notifications, track date of the last health check-up
                if domain.last_health_check:
                    logger.info(
                        "Domain has a prior health check-up date: %s",
                        domain.last_health_check,
                    )
                    last_health_check = domain.last_health_check
                # If the date is empty (no past checks), limit notifications with the purchase date
                else:
                    last_health_check = domain.creation
                    logger.info(
                        "No prior health check so set date to %s", last_health_check
                    )
                logger.info("Domain is currently considered to be %s", health)

                # Check domain name with VT's Domain Report
                vt_results = self.get_domain_report(domain_name)
                if vt_results["result"] == "success":
                    logger.info("Received results for %s from VirusTotal", domain_name)
                    lab_results[domain]["vt_results"] = vt_results["data"]

                    # Check if VT returned the ``categories`` key with a list
                    if "categories" in vt_results["data"]:
                        domain_categories = vt_results["data"]["categories"]
                    # Locate category data spread-out across multiple keys
                    # One or more ``* category`` keys for specific third-parties
                    # Example: ``Forcepoint ThreatSeeker category``
                    search_key = "category"
                    more_categories = [
                        f"{val.title()} ({key.replace(' category', '')})"
                        for key, val in vt_results["data"].items()
                        if search_key in key
                    ]
                    domain_categories.extend(more_categories)

                    # Make categories unique
                    domain_categories = list(set(domain_categories))

                    # Check if VirusTotal has any detections for URLs or malware samples
                    if "BitDefender domain info" in vt_results["data"]:
                        bd_msg = vt_results["data"]["BitDefender domain info"]
                        logger.warning(
                            "Domain %s is known to Bitdefender as potentially maliciously: %s",
                            domain_name,
                            bd_msg,
                        )
                        burned = True
                        burned_explanations.append(
                            "Flagged by Bitdefender with this message:\n{}".format(bd_msg)
                        )
                    if "detected_downloaded_samples" in vt_results["data"]:
                        # TODO: Potentially collect permalink and scan data from VT's ``/file/report`` endpoint
                        if len(vt_results["data"]["detected_downloaded_samples"]) > 0:
                            total_detections = len(
                                vt_results["data"]["detected_downloaded_samples"]
                            )
                            logger.warning(
                                "Domain %s is tied to %s VirusTotal malware sample(s)",
                                domain_name,
                                total_detections,
                            )
                            burned = True
                            detections = []
                            for detection in vt_results["data"][
                                "detected_downloaded_samples"
                            ]:
                                detections.append(
                                    "VT downloaded a file with a SHA256 hash of {} which had {} detections for malware on {}".format(
                                        detection["sha256"],
                                        detection["positives"],
                                        detection["date"],
                                    )
                                )
                            burned_explanations.append(
                                "Tied to {} VirusTotal malware sample(s):\n{}".format(
                                    total_detections, "\n".join(detections)
                                )
                            )
                    if "detected_urls" in vt_results["data"]:
                        # TODO: Potentially collect permalink and scan data from VT's ``/url/report`` endpoint
                        if len(vt_results["data"]["detected_urls"]) > 0:
                            total_detections = len(vt_results["data"]["detected_urls"])
                            logger.warning(
                                "Domain %s has a positive malware detection on VirusTotal",
                                domain_name,
                            )
                            burned = True
                            detections = []
                            for detection in vt_results["data"]["detected_urls"]:
                                detections.append(
                                    "{} has {} positive detections from {}".format(
                                        detection["url"],
                                        detection["positives"],
                                        detection["scan_date"],
                                    )
                                )
                            burned_explanations.append(
                                "Domain has {} malware detections on VirusTotal:\n{}".format(
                                    total_detections, "\n".join(detections)
                                )
                            )
                    # Check for undetected submissions as potential early warnings
                    if "undetected_downloaded_samples" in vt_results["data"]:
                        if len(vt_results["data"]["undetected_downloaded_samples"]) > 0:
                            for scan in vt_results["data"][
                                "undetected_downloaded_samples"
                            ]:
                                scan_date = datetime.datetime.strptime(
                                    scan["date"].split(" ")[0], "%Y-%m-%d"
                                )
                                if scan_date.date() >= last_health_check:
                                    warning_msg = "File hosted under {} was submitted to VirusTotal on {}, after domain's last health check on {}: {}".format(
                                        domain_name,
                                        scan["date"],
                                        last_health_check,
                                        scan["sha256"],
                                    )
                                    warnings.append(warning_msg)
                                else:
                                    logger.info(
                                        "Ignored warning because %s is not >= %s",
                                        scan_date.date(),
                                        last_health_check,
                                    )
                    if "undetected_urls" in vt_results["data"]:
                        if len(vt_results["data"]["undetected_urls"]) > 0:
                            for scan in vt_results["data"]["undetected_urls"]:
                                # For some reason, these results are lists instead of dicts
                                scan_domain = scan[0]
                                scan_uri = scan[1]
                                scan_positives = scan[2]
                                scan_total = scan[3]
                                scan_date = scan[4]
                                scan_date = datetime.datetime.strptime(
                                    scan_date.split(" ")[0], "%Y-%m-%d"
                                )
                                if scan_date.date() >= last_health_check:
                                    warning_msg = "This URL was submitted to VirusTotal on {}, after domain's last health check on {}: {}{}".format(
                                        scan_date,
                                        last_health_check,
                                        scan_domain,
                                        scan_uri,
                                    )
                                    warnings.append(warning_msg)
                                else:
                                    logger.info(
                                        "Ignored warning because %s is not >= %s",
                                        scan_date.date(),
                                        last_health_check,
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
                        "Tagged with one or more undesirable categories: {bad_cat}".format(
                            bad_cat=", ".join(bad_categories)
                        )
                    )

                # Assemble the dictionary to return for this domai
                lab_results[domain]["burned"] = burned
                lab_results[domain]["categories"] = domain_categories
                lab_results[domain]["warnings"]["messages"] = warnings
                lab_results[domain]["warnings"]["total"] = len(warnings)
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
