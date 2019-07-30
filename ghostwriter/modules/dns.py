#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains the tools required for collecting and parsing
DNS records.
"""

import dns.resolver


class DNSCollector(object):
    """Class to retrieve DNS records and perform some basic analysis."""
    # Setup a DNS resolver so a timeout can be set
    # No timeout means a very, very long wait if a domain has no records
    resolver = dns.resolver.Resolver()
    resolver.timeout = 1
    resolver.lifetime = 1

    def __init__(self):
        """Everything that should be initiated with a new object goes here."""
        pass

    def get_dns_record(self, domain, record_type):
        """Collect the specified DNS record type for the target domain.

        Parameters:
        domain          The domain to be used for DNS record collection
        record_type     The DNS record type to collect
        """
        answer = self.resolver.query(domain, record_type)
        return answer

    def parse_dns_answer(self, dns_record):
        """Parse the provided DNS record and return a list containing each item.

        Parameters:
        dns_record      The DNS record to be parsed
        """
        temp = []
        for rdata in dns_record.response.answer:
            for item in rdata.items:
                temp.append(item.to_text())
        return ", ".join(temp)

    def return_dns_record_list(self, domain, record_type):
        """Collect and parse a DNS record for the given domain and DNS record
        type and then return a list.

        Parameters:
        domain          The domain to be used for DNS record collection
        record_type     The DNS record type to collect
        """
        record = self.get_dns_record(domain, record_type)
        return self.parse_dns_answer(record)
