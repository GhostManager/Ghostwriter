"""
This module contains the tools required for collecting and parsing DNS records.
"""

# Standard Libraries
import asyncio
import logging
from asyncio import Semaphore
from typing import Union

# 3rd Party Libraries
from dns import asyncresolver
from dns.resolver import NXDOMAIN, Answer, NoAnswer

# Using __name__ resolves to ghostwriter.modules.dns_toolkit
logger = logging.getLogger(__name__)


class DNSCollector(object):
    """
    Retrieve and parse DNS records asynchronously.

    **Parameters**

    ``concurrent_limit``
        Set limit on number of concurrent DNS requests to avoid hitting system limits
    """

    # Configure the DNS resolver to be asynchronous and use specific nameservers
    resolver = asyncresolver.Resolver()
    resolver.lifetime = 1
    resolver.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]

    def __init__(self, concurrent_limit=50):
        # Limit used for Semaphore to avoid hitting system limits on open requests
        self.semaphore = Semaphore(value=concurrent_limit)

    async def _query(
        self, domain: str, record_type: str
    ) -> Union[Answer, NXDOMAIN, NoAnswer]:
        """
        Execute a DNS query for the target domain and record type.

        **Parameters**

        ``domain``
            Domain to be used for DNS record collection
        ``record_type``
            DNS record type to collect
        """
        try:
            # Wait to acquire the semaphore to avoid too many concurrent DNS requests
            await self.semaphore.acquire()
            answer = await self.resolver.resolve(domain, record_type)
        except Exception as e:
            answer = e
        # Release semaphore to allow next request
        self.semaphore.release()
        return answer

    async def _parse_answer(self, dns_record: Answer) -> list:
        """
        Parse the provided instance of ``dns.resolver.Answer``.

        **Parameters**

        ``dns_record``
            Instance of ``dns.resolve.Answer``
        """
        record_list = []
        for rdata in dns_record.response.answer:
            for item in rdata.items:
                record_list.append(item.to_text())
        return record_list

    async def _fetch_record(self, domain: str, record_type: str) -> dict:
        """
        Fetch a DNS record for the given domain and record type.

        **Parameters**

        ``domain``
            Domain to be used for DNS record collection
        ``record_type``
            DNS record type to collect (A, NS, SOA, TXT, MX, CNAME, DMARC)
        """
        logger.debug("Fetching %s records for %s", record_type, domain)
        # Prepare the results dictionary
        result = {}
        result[domain] = {}
        result[domain]["domain"] = domain

        # Handle DMARC as a special record type
        if record_type.lower() == "dmarc":
            record_type = "A"
            query_type = "dmarc_record"
            query_domain = "_dmarc." + domain
        else:
            query_type = record_type.lower() + "_record"
            query_domain = domain

        # Execute query and await completion
        response = await self._query(query_domain, record_type)

        # Only parse result if it's an ``Answer``
        if isinstance(response, Answer):
            record = await self._parse_answer(response)
            result[domain][query_type] = record
        else:
            # Return the type of exception (e.g., NXDOMAIN)
            result[domain][query_type] = type(response).__name__
        return result

    async def _prepare_async_dns(self, domains: list, record_types: list) -> list:
        """
        Prepare asynchronous DNS queries for a list of domain names.

        **Parameters**

        ``domains``
            Queryset of :model:`shepherd.Domain` entries
        ``record_types``
            List of record types represented as strings (e.g., ["A", "TXT"])
        """
        tasks = []
        # For each domain, create a task for each DNS record of interest
        for domain in domains:
            for record_type in record_types:
                tasks.append(
                    self._fetch_record(domain=domain.name, record_type=record_type)
                )
        # Gather all tasks for execution
        all_tasks = await asyncio.gather(*tasks)
        return all_tasks

    def run_async_dns(self, domains: list, record_types: list) -> dict:
        """
        Execute asynchronous DNS queries for a list of domain names.

        **Parameters**

        ``domains``
            List of domain names
        ``record_types``
            List of record types represented as strings (e.g., ["A", "TXT"])
        """
        # Setup an event loop
        event_loop = asyncio.get_event_loop()
        # Use an event loop (instead of ``asyncio.run()``) to easily get list of results
        results = event_loop.run_until_complete(
            self._prepare_async_dns(domains=domains, record_types=record_types)
        )
        # Result is a list of dicts – seven for each domain name
        combined = {}
        # Combine all dicts with the same domain name
        for res in results:
            for key, value in res.items():
                if key in combined:
                    combined[key].update(value)
                else:
                    combined[key] = {}
                    combined[key].update(value)
        return combined
