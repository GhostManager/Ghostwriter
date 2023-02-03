#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains the ``DomainReview`` class. The class checks if a domain name is
properly categorized, has not been flagged in VirusTotal, or tagged with a bad category.
"""

# Standard Libraries
import logging
import sys
import traceback
from time import sleep

# 3rd Party Libraries
import requests

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import VirusTotalConfiguration

# Disable requests warnings for things like disabling certificate checking
requests.packages.urllib3.disable_warnings()

# Using __name__ resolves to ghostwriter.modules.review
logger = logging.getLogger(__name__)


class DomainReview:
    """
    Pull a list of domain names and check their web reputation.

    **Parameters**

    ``domain_queryset``
        Queryset for :model:`shepherd:Domain`
    ``sleep_time_override``
        Number of seconds to sleep between VirusTotal API requests
        (overrides global configuration)
    """

    # API endpoints
    VIRUSTOTAL_BASE_API_URL = "https://www.virustotal.com/api/v3"

    # Categories we don't want to see
    # These are lowercase to avoid inconsistencies with how each service might return the categories
    blocklist = [
        "adult/mature content",
        "extreme",
        "gambling",
        "hacking",
        "malicious outbound data/botnets",
        "malicious sources",
        "malicious sources/malnets",
        "malware repository",
        "nudity",
        "phishing",
        "placeholders",
        "pornography",
        "potentially unwanted software",
        "scam/questionable/illegal",
        "spam",
        "spyware and malware",
        "suspicious",
        "violence/hate/racism",
        "weapons",
        "web ads/analytics",
    ]

    # Variables for web browsing
    session = requests.Session()

    def __init__(self, domain_queryset, sleep_time_override=None):
        # Get API configuration
        self.virustotal_config = VirusTotalConfiguration.get_solo()
        if self.virustotal_config.enable is False:
            logger.error("Tried to start a domain review without VirusTotal configured and enabled")
            sys.exit()

        self.domain_queryset = domain_queryset

        # Override globally configured sleep time
        if len(domain_queryset) == 1:
            self.sleep_time = 0
        elif sleep_time_override:
            self.sleep_time = sleep_time_override
        else:
            self.sleep_time = self.virustotal_config.sleep_time

    def get_domain_report(self, domain, ignore_case=False, subdomains=False):
        """
        Look-up the provided domain name with VirusTotal's Domains API endpoint.

        Ref: https://developers.virustotal.com/reference#domain-report

        If ``subdomains`` is set to ``True``, the function will return a list of subdomains
        from the VirusTotal Domains Relationships endpoint.

        Ref: https://developers.virustotal.com/reference#subdomains

        **Parameters**

        ``domain``
            Domain name to search
        ``ignore_case``
            Do not convert domain name to lowercase (Default: False)
        ``subdomains``
            Return a list of subdomains (Default: False)
        """
        if subdomains:
            virustotal_endpoint_uri = "/domains/{domain}/relationships/subdomains".format(domain=domain)
        else:
            virustotal_endpoint_uri = "/domains/{domain}".format(domain=domain)

        url = self.VIRUSTOTAL_BASE_API_URL + virustotal_endpoint_uri
        results = {}
        results["result"] = "success"
        if self.virustotal_config.enable:
            # The VT API is case sensitive, so domains should always be lowercase
            if not ignore_case:
                domain = domain.lower()
            try:
                headers = {
                    "x-apikey": self.virustotal_config.api_key,
                }
                req = self.session.get(url, headers=headers)
                if req.ok:
                    vt_data = req.json()
                    results["data"] = vt_data["data"]["attributes"]
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
                domain_categories = {}
                bad_categories = []
                burned_explanations = []
                lab_results[domain.id] = {}
                warnings = []
                lab_results[domain.id]["domain"] = domain.name
                lab_results[domain.id]["domain_qs"] = domain
                lab_results[domain.id]["warnings"] = {}
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
                    logger.info("No prior health check so set date to %s", last_health_check)
                logger.info("Domain is currently considered to be %s", health)

                # Check domain name with VT's Domain Report
                vt_results = self.get_domain_report(domain_name)
                if vt_results["result"] == "success":
                    logger.info("Received results for %s from VirusTotal", domain_name)

                    domain_categories = {}
                    lab_results[domain.id]["vt_results"] = vt_results["data"]

                    # Check if the domain is tagged as DGA
                    if "tags" in vt_results["data"]:
                        if "dga" in vt_results["data"]["tags"]:
                            burned = True
                            burned_explanations.append(
                                "Domain is tagged with `DGA` for domain generation algorithm, and likely flagged for malware."
                            )

                    # Check if VT returned the ``categories`` key with a list
                    if "categories" in vt_results["data"]:
                        # Store the categories and check each one against the blocklist
                        domain_categories = vt_results["data"]["categories"]
                        for source, category in domain_categories.items():
                            if category.lower() in self.blocklist:
                                bad_categories.append(category)
                                logger.warning(
                                    "%s has assigned %s an undesirable category: %s",
                                    source,
                                    domain_name,
                                    category,
                                )
                                burned = True
                                burned_explanations.append(
                                    f"{source} has assigned the domain an undesirable category: {category}."
                                )

                    # Check for any detections
                    if "last_analysis_stats" in vt_results["data"]:
                        analysis_stats = vt_results["data"]["last_analysis_stats"]
                        if analysis_stats["malicious"] > 0:
                            burned = True
                            burned_explanations.append("A VirusTotal scanner has flagged the domain as malicious.")
                            logger.warning(
                                "A VirusTotal scanner has flagged the %s as malicious",
                                domain_name,
                            )

                    # Check the VT community voting
                    if "total_votes" in vt_results["data"]:
                        votes = vt_results["data"]["total_votes"]
                        if votes["malicious"] > 0:
                            burned = True
                            burned_explanations.append(
                                "There are {} VirusTotal community votes flagging the the domain as malicious.".format(
                                    votes["malicious"]
                                )
                            )
                            logger.warning(
                                "There are %s VirusTotal community votes flagging the the domain as malicious",
                                votes["malicious"],
                            )

                else:
                    lab_results[domain.id]["vt_results"] = "none"
                    logger.warning("Did not receive results for %s from VirusTotal", domain_name)

                # Assemble the dictionary to return for this domain
                lab_results[domain.id]["burned"] = burned
                lab_results[domain.id]["categories"] = domain_categories
                lab_results[domain.id]["warnings"]["messages"] = warnings
                lab_results[domain.id]["warnings"]["total"] = len(warnings)
                if burned:
                    lab_results[domain.id]["burned_explanation"] = burned_explanations

                # Sleep for a while for VirusTotal's API
                sleep(self.sleep_time)
            else:
                logger.warning(
                    "Domain %s is expired, so skipped it",
                    domain.name,
                )
        return lab_results
