#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This class accepts a list of domains from a provided Django query set and
then reviews each one to ensure it is ready to be used for an op. This
involves checking to see if the domain is properly categorized, the domain has
not been flagged in VirusTotal or tagged with a bad category, and the domain
is not blacklisted for spam.

DomainReview checks the domain against VirusTotal, Cisco Talos, Bluecoat,
IBM X-Force, Fortiguard, TrendMicro, OpeDNS, and MXToolbox. Domains will also
be checked against malwaredomains.com's list of reported domains.
"""

import os
import re
import json
import shutil
import base64
from time import sleep

from django.conf import settings

import requests
from lxml import etree
from bs4 import BeautifulSoup


# Disable requests warnings for things like disabling certificate checking
requests.packages.urllib3.disable_warnings()


class DomainReview(object):
    """Class to pull a list of registered domains belonging to a Namecheap
    account and then check the web reputation of each domain.
    """
    # API endpoints
    malwaredomains_url = 'http://mirror1.malwaredomains.com/files/justdomains'
    virustotal_domain_report_uri = \
        'https://www.virustotal.com/vtapi/v2/domain/report?apikey={}&domain={}'
    # Categories we don't want to see
    # These are lowercase to avoid inconsistencies with how each service might
    # return the categories
    blacklisted = ['phishing', 'web ads/analytics', 'suspicious',
                   'placeholders', 'pornography', 'spam', 'gambling',
                   'scam/questionable/illegal', 'malicious sources/malnets']
    # Variables for web browsing
    useragent = \
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
    session = requests.Session()

    def __init__(self, domain_queryset):
        """Everything that needs to be setup when a new DomainReview object is
        created goes here.
        """
        # Domain query results from the Django models
        self.domain_queryset = domain_queryset
        # Try to get the sleep time configured in settings
        try:
            self.request_delay = settings.DOMAINCHECK_CONFIG['sleep_time']
        except Exception:
            self.request_delay = 20
        try:
            self.virustotal_api_key = \
                settings.DOMAINCHECK_CONFIG['virustotal_api_key']
        except Exception:
            self.virustotal_api_key = None
            print('[!] A VirusTotal API key could not be pulled from '
                  'settings.py. Review settings to perform VirusTotal checks.')
            exit()

    def check_virustotal(self, domain, ignore_case=False):
        """Check the provided domain name with VirusTotal. VirusTotal's API is
        case sensitive, so the domain will be converted to lowercase by
        default. This can be disabled using the ignore_case parameter.

        This uses the VirusTotal /domain/report endpoint:

        https://developers.virustotal.com/v2.0/reference#domain-report
        """
        if self.virustotal_api_key:
            if not ignore_case:
                domain = domain.lower()
            try:
                req = self.session.get(self.virustotal_domain_report_uri.
                                       format(self.virustotal_api_key, domain))
                vt_data = req.json()
            except Exception:
                vt_data = None
            return vt_data
        else:
            return None

    def check_talos(self, domain):
        """Check the provided domain's category as determined by
        Cisco Talos.
        """
        categories = []
        cisco_talos_uri = 'https://talosintelligence.com/sb_api/query_lookup?query=%2Fapi%2Fv2%2Fdetails%2Fdomain%2F&query_entry={}&offset=0&order=ip+asc'
        headers = {'User-Agent': self.useragent,
                   'Referer': 'https://www.talosintelligence.com/reputation_center/lookup?search=' + domain}
        try:
            req = self.session.get(
                cisco_talos_uri.format(domain),
                headers=headers)
            if req.ok:
                json_data = req.json()
                print(req.text)
                if 'category' in json_data:
                    categories.append(json_data['category']['description'])
                else:
                    categories.append('Uncategorized')
            else:
                print('[!] Cisco Talos check request failed. Talos did not '
                        'return a 200 response.')
                print('L.. Request returned status "{}"'.
                        format(req.status_code))
        except Exception as error:
            print('[!] Cisco Talos request failed: {}'.format(error))
        return categories

    def check_ibm_xforce(self, domain):
        """Check the provided domain's category as determined by
        IBM X-Force.
        """
        categories = []
        xforce_uri = 'https://exchange.xforce.ibmcloud.com/url/{}'.\
            format(domain)
        headers = {'User-Agent': self.useragent,
                   'Accept': 'application/json, text/plain, */*',
                   'x-ui': 'XFE',
                   'Origin': xforce_uri,
                   'Referer': xforce_uri}
        xforce_api_uri = 'https://api.xforce.ibmcloud.com/url/{}'.\
            format(domain)
        try:
            req = self.session.get(
                xforce_api_uri,
                headers=headers,
                verify=False)
            if req.ok:
                response = req.json()
                if not response['result']['cats']:
                    categories.append('Uncategorized')
                else:
                    # Parse all dictionary keys and append to single string to
                    # get Category names
                    for key in response['result']['cats']:
                        categories.append(key)
            # IBM X-Force returns a 404 with {"error":"Not found."} if the
            # domain is unknown
            elif req.status_code == 404:
                categories.append('Unknown')
            else:
                print('[!] IBM X-Force check request failed. X-Force did not '
                      'return a 200 response.')
                print('L.. Request returned status "{}"'.
                      format(req.status_code))
        except Exception as error:
            print('[!] IBM X-Force request failed: {}'.
                  format(error))
        return categories

    def check_fortiguard(self, domain):
        """Check the provided domain's category as determined by
        Fortiguard Webfilter.
        """
        categories = []
        fortiguard_uri = 'https://fortiguard.com/webfilter?q=' + domain
        headers = {'User-Agent': self.useragent,
                   'Origin': 'https://fortiguard.com',
                   'Referer': 'https://fortiguard.com/webfilter'}
        try:
            req = self.session.get(fortiguard_uri, headers=headers)
            if req.ok:
                """
                Example HTML result:
                <div class="well">
                    <div class="row">
                        <div class="col-md-9 col-sm-12">
                            <h4 class="info_title">Category: Education</h4>
                """
                # TODO: Might be best to BS4 for this rather than regex
                cat = re.findall('Category: (.*?)" />', req.text, re.DOTALL)
                categories.append(cat[0])
            else:
                print('[!] Fortiguard check request failed. Fortiguard did '
                      'not return a 200 response.')
                print('L.. Request returned status "{}"'.
                      format(req.status_code))
        except Exception as error:
            print('[!] Fortiguard request failed: {}'.format(error))
        return categories

    def check_bluecoat(self, domain, ocr=True):
        """Check the provided domain's category as determined by
        Symantec Bluecoat.
        """
        categories = []
        bluecoat_uri = 'https://sitereview.bluecoat.com/#/'
        bluecoat_captcha = 'https://sitereview.bluecoat.com/resource/captcha-request'
        bluecoat_lookup = 'https://sitereview.bluecoat.com/resource/lookup'
        post_data_1 = {'check': 'captcha'}
        post_data_2 = {'url': domain, 'captcha': ''}
        headers = {'User-Agent': self.useragent}
        try:
            response = self.session.get(
                bluecoat_uri,
                headers=headers,
                verify=False)
            response = self.session.post(
                bluecoat_captcha,
                headers=headers,
                json=post_data_1,
                verify=False)
            # Update headers with CSRF token
            headers = {'User-Agent': self.useragent,
                    'Content-Type': 'application/json; charset=UTF-8',
                    'Referer': 'https://sitereview.bluecoat.com/lookup',
                    'X-XSRF-TOKEN': self.session.cookies['XSRF-TOKEN']}
            response = self.session.post(
                bluecoat_lookup,
                headers=headers,
                json=post_data_2,
                verify=False)
            root = etree.fromstring(response.text)
            for node in root.xpath(
                '//CategorizationResult//categorization//categorization//name'
                ):
                categories.append(node.text)
        except Exception as error:
            print('[!] Bluecoat request failed: {0}'.format(error))
        return categories


    def check_mxtoolbox(self, domain):
        """Check if the provided domain is blacklisted as spam as determined
        by MX Toolkit.
        """
        issues = []
        mxtoolbox_url = \
            'https://mxtoolbox.com/Public/Tools/BrandReputation.aspx'
        headers = {'User-Agent': self.useragent,
                   'Origin': mxtoolbox_url,
                   'Referer': mxtoolbox_url}
        try:
            response = self.session.get(url=mxtoolbox_url, headers=headers)
            soup = BeautifulSoup(response.content, 'lxml')
            viewstate = soup.select('input[name=__VIEWSTATE]')[0]['value']
            viewstategenerator = \
                soup.select('input[name=__VIEWSTATEGENERATOR]')[0]['value']
            eventvalidation = \
                soup.select('input[name=__EVENTVALIDATION]')[0]['value']
            data = {
                    '__EVENTTARGET': '',
                    '__EVENTARGUMENT': '',
                    '__VIEWSTATE': viewstate,
                    '__VIEWSTATEGENERATOR': viewstategenerator,
                    '__EVENTVALIDATION': eventvalidation,
                    'ctl00$ContentPlaceHolder1$brandReputationUrl': domain,
                    'ctl00$ContentPlaceHolder1$brandReputationDoLookup':
                    'Brand Reputation Lookup',
                    'ctl00$ucSignIn$hfRegCode': 'missing',
                    'ctl00$ucSignIn$hfRedirectSignUp':
                    '/Public/Tools/BrandReputation.aspx',
                    'ctl00$ucSignIn$hfRedirectLogin': '',
                    'ctl00$ucSignIn$txtEmailAddress': '',
                    'ctl00$ucSignIn$cbNewAccount': 'cbNewAccount',
                    'ctl00$ucSignIn$txtFullName': '',
                    'ctl00$ucSignIn$txtModalNewPassword': '',
                    'ctl00$ucSignIn$txtPhone': '',
                    'ctl00$ucSignIn$txtCompanyName': '',
                    'ctl00$ucSignIn$drpTitle': '',
                    'ctl00$ucSignIn$txtTitleName': '',
                    'ctl00$ucSignIn$txtModalPassword': ''
            }
            response = self.session.post(
                url=mxtoolbox_url,
                headers=headers,
                data=data)
            soup = BeautifulSoup(response.content, 'lxml')
            if soup.select('div[id=ctl00_ContentPlaceHolder1_noIssuesFound]'):
                issues.append('No issues found')
            else:
                if (
                    soup.select(
                        'div[id=ctl00_ContentPlaceHolder1_'
                        'googleSafeBrowsingIssuesFound]'
                        )
                  ):
                    issues.append('Google SafeBrowsing Issues Found.')
                if (
                    soup.select(
                        'div[id=ctl00_ContentPlaceHolder1_'
                        'phishTankIssuesFound]'
                        )
                  ):
                    issues.append('PhishTank Issues Found')
        except Exception:
            print('[!] Error retrieving Google SafeBrowsing and PhishTank '
                  'reputation!')
        return issues

    def check_opendns(self, domain):
        """Check the provided domain's category as determined by the
        OpenDNS community.
        """
        categories = []
        opendns_uri = 'https://domain.opendns.com/{}'
        headers = {'User-Agent': self.useragent}
        try:
            response = self.session.get(
                opendns_uri.format(domain),
                headers=headers,
                verify=False)
            soup = BeautifulSoup(response.content, 'lxml')
            tags = soup.find('span', {'class': 'normal'})
            if tags:
                categories = tags.text.strip().split(', ')
            else:
                categories.append('No Tags')
        except Exception as error:
            print('[!] OpenDNS request failed: {0}'.format(error))
        return categories

    def check_trendmicro(self, domain):
        """Check the provided domain's category as determined by
        Trend Micro.
        """
        categories = []
        trendmicro_uri = \
            'https://global.sitesafety.trendmicro.com/'
        trendmicro_stage_1_uri = \
            'https://global.sitesafety.trendmicro.com/lib/idn.php'
        trendmicro_stage_2_uri = \
            'https://global.sitesafety.trendmicro.com/result.php'
        headers = {'User-Agent': self.useragent}
        headers_stage_1 = {
                           'Host': 'global.sitesafety.trendmicro.com',
                           'Accept': '*/*',
                           'Origin':
                           'https://global.sitesafety.trendmicro.com',
                           'X-Requested-With': 'XMLHttpRequest',
                           'User-Agent': self.useragent,
                           'Content-Type': 'application/x-www-form-urlencoded',
                           'Referer': 'https://global.sitesafety.trendmicro.'
                                      'com/index.php',
                           'Accept-Encoding': 'gzip, deflate',
                           'Accept-Language': 'en-US, en;q=0.9'
                          }
        headers_stage_2 = {
                           'Origin':
                           'https://global.sitesafety.trendmicro.com',
                           'Content-Type': 'application/x-www-form-urlencoded',
                           'User-Agent': self.useragent,
                           'Accept': 'text/html, application/xhtml+xml, '
                           'application/xml;q=0.9, image/webp, image/apng, '
                           '*/*;q=0.8',
                           'Referer': 'https://global.sitesafety.trendmicro.'
                                      'com/index.php',
                           'Accept-Encoding': 'gzip, deflate',
                           'Accept-Language': 'en-US, en;q=0.9'
                          }
        data_stage_1 = {'url': domain}
        data_stage_2 = {'urlname': domain,
                        'getinfo': 'Check Now'
                        }
        try:
            response = self.session.get(
                trendmicro_uri,
                headers=headers)
            response = self.session.post(
                trendmicro_stage_1_uri,
                headers=headers_stage_1,
                data=data_stage_1)
            response = self.session.post(
                trendmicro_stage_2_uri,
                headers=headers_stage_2,
                data=data_stage_2)
            # Check if session was redirected to /captcha.php
            if 'captcha' in response.url:
                print('[!] TrendMicro responded with a reCAPTCHA, so cannot '
                      'proceed with TrendMicro.')
                print('L.. You can try solving it yourself: '
                      'https://global.sitesafety.trendmicro.com/captcha.php')
            else:
                soup = BeautifulSoup(response.content, 'lxml')
                tags = soup.find('div', {'class': 'labeltitlesmallresult'})
                if tags:
                    categories = tags.text.strip().split(', ')
                else:
                    categories.append('Uncategorized')
        except Exception as error:
            print('[!] Trend Micro request failed: {0}'.format(error))
        return categories

    def download_malware_domains(self):
        """Downloads the malwaredomains.com list of malicious domains."""
        headers = {'User-Agent': self.useragent}
        response = self.session.get(
            url=self.malwaredomains_url,
            headers=headers,
            verify=False)
        malware_domains = response.text
        if response.status_code == 200:
            return malware_domains
        else:
            print('[!] Error reaching: {}, Status: {}'.
                  format(self.malwaredomains_url, response.status_code))
            return None

    def check_domain_status(self):
        """Check the status of each domain in the provided list collected from
        the Domain model. Each domain will be checked to ensure the domain is
        not flagged/blacklisted. A domain will be considered burned if
        VirusTotal returns detections for the domain or one of the domain's
        categories appears in the list of bad categories.

        VirusTotal allows 4 requests every 1 minute. A minimum of 20 seconds
        is recommended to allow for some consideration on the service.

        """
        lab_results = {}
        malware_domains = self.download_malware_domains()
        for domain in self.domain_queryset:
            print('[+] Starting update of {}'.format(domain.name))
            burned_dns = False
            domain_categories = []
            # Sort the domain information from queryset
            domain_name = domain.name
            health = domain.health_status
            print('[+] Domain is currently flagged as {}'.format(health))
            # Check if domain is known to be burned and skip it if so
            # This just saves time and operators can edit a domain and set
            # status to `Healthy` as needed
            # The domain will be included in the next update after the edit
            if health != 'Healthy':
                burned = False
            else:
                burned = True
            if not burned:
                burned_explanations = []
                if domain.burned_explanation:
                    burned_explanations.append(domain.burned_explanation)
                # Check if domain is flagged for malware
                if malware_domains:
                    if domain_name in malware_domains:
                        print('[!] {}: Identified as a known malware domain '
                              '(malwaredomains.com)!'.format(domain_name))
                        burned = True
                        burned_explanations.append(
                            'Flagged by malwaredomains.com')
                # Check domain name with VirusTotal
                vt_results = self.check_virustotal(domain_name)
                if vt_results:
                    if 'categories' in vt_results:
                        domain_categories = vt_results['categories']
                    # Check if VirusTotal has any detections for URLs or
                    #  malware samples
                    if 'detected_downloaded_samples' in vt_results:
                        if len(vt_results['detected_downloaded_samples']) > 0:
                            print('[!] {}: Identified as having a downloaded '
                                  'sample on VirusTotal!'.format(domain_name))
                            burned = True
                            burned_explanations.append('Tied to a VirusTotal '
                                                       'detected malware'
                                                       'sample')
                    if 'detected_urls' in vt_results:
                        if len(vt_results['detected_urls']) > 0:
                            print('[!] {}: Identified as having a URL '
                                  'detection on VirusTotal!'.
                                  format(domain_name))
                            burned = True
                            burned_explanations.append('Tied to a VirusTotal '
                                                       'detected URL')
                    # Get passive DNS results from VirusTotal JSON
                    ip_addresses = []
                    if 'resolutions' in vt_results:
                        for address in vt_results['resolutions']:
                            ip_addresses.append({
                                'address': address['ip_address'],
                                'timestamp': address['last_resolved'].
                                split(' ')[0]})
                    bad_addresses = []
                if burned_dns:
                    print('[*] {}: Identified as pointing to suspect IP '
                          'addresses (VirusTotal passive DNS).'.
                          format(domain_name))
                    health_dns = 'Flagged DNS ({})'.\
                        format(', '.join(bad_addresses))
                else:
                    health_dns = "Healthy"
                # Collect categories from the other sources
                xforce_results = self.check_ibm_xforce(domain_name)
                domain_categories.extend(xforce_results)
                talos_results = self.check_talos(domain_name)
                domain_categories.extend(talos_results)
                bluecoat_results = self.check_bluecoat(domain_name)
                domain_categories.extend(bluecoat_results)
                fortiguard_results = self.check_fortiguard(domain_name)
                domain_categories.extend(fortiguard_results)
                opendns_results = self.check_opendns(domain_name)
                domain_categories.extend(opendns_results)
                trendmicro_results = self.check_trendmicro(domain_name)
                domain_categories.extend(trendmicro_results)
                mxtoolbox_results = self.check_mxtoolbox(domain_name)
                domain_categories.extend(domain_categories)
                # Make categories unique
                domain_categories = list(set(domain_categories))
                # Check if any categopries are suspect
                bad_categories = []
                for category in domain_categories:
                    if category.lower() in self.blacklisted:
                        bad_categories.append(category.capitalize())
                if bad_categories:
                    burned = True
                    burned_explanations.append('Tagged with a bad category')
                # Assemble the dictionary to return for this domain
                lab_results[domain] = {}
                lab_results[domain]['categories'] = {}
                lab_results[domain]['burned'] = burned
                lab_results[domain]['health_dns'] = health_dns
                lab_results[domain]['burned_explanation'] = \
                    ', '.join(burned_explanations)
                lab_results[domain]['categories']['all'] = \
                    ', '.join(bad_categories)
                lab_results[domain]['categories']['bad'] = \
                    ', '.join(domain_categories)
                lab_results[domain]['categories']['talos'] = \
                    ', '.join(talos_results)
                lab_results[domain]['categories']['xforce'] = \
                    ', '.join(xforce_results)
                lab_results[domain]['categories']['opendns'] = \
                    ', '.join(opendns_results)
                lab_results[domain]['categories']['bluecoat'] = \
                    ', '.join(bluecoat_results)
                lab_results[domain]['categories']['mxtoolbox'] = \
                    ', '.join(mxtoolbox_results)
                lab_results[domain]['categories']['fortiguard'] = \
                    ', '.join(fortiguard_results)
                lab_results[domain]['categories']['trendmicro'] = \
                    ', '.join(trendmicro_results)
                # Sleep for a while for VirusTotal's API
                sleep(self.request_delay)
        return lab_results
