"""
This contains utilities for checking the health of Ghostwriter services not covered
by `django-health-check.
"""

# Standard Libraries
import dataclasses
from datetime import datetime
import os

# 3rd Party Libraries
import requests

# Django Imports
from django.conf import settings
from django.core.cache import caches as django_caches
from django.db import OperationalError, connections
from health_check import HealthCheck
from health_check.exceptions import (
    HealthCheckException,
    ServiceReturnedUnexpectedResult,
    ServiceUnavailable,
    ServiceWarning,
)


@dataclasses.dataclass
class HasuraBackend(HealthCheck):
    """
    Health check for the Hasura GraphQL Engine. This checks the ``/healthz`` API
    endpoint. The :view:`status:HealthCheckCustomView` view includes this in its
    explicit health check list.

    Ref: https://hasura.io/docs/latest/api-reference/health/
    """

    critical_service = True

    @property
    def graphql_host(self):
        """Retrieve the GraphQL host from the environment variable or use the default."""

        return os.getenv("GRAPHQL_HOST", "graphql_engine")

    def run(self):
        """Check the status of the backend service."""
        try:
            response = requests.get(
                f"http://{self.graphql_host}:8080/healthz",
                timeout=5,
            )
            if response.ok:
                content = response.text
                if "OK" in content:
                    return
                elif "WARN" in content:
                    raise ServiceWarning(f"Hasura reported a warning: {content}")
            else:
                raise HealthCheckException("Hasura reported an error")
        except requests.exceptions.ConnectionError as e:
            raise ServiceUnavailable("Hasura GraphQL Engine is not responding") from e
        except requests.exceptions.Timeout as e:
            raise ServiceUnavailable("Hasura GraphQL Engine request timed out") from e
        except requests.exceptions.RequestException as e:
            raise ServiceReturnedUnexpectedResult(
                "Exception encountered when connecting to Hasura"
            ) from e

    def __repr__(self):
        """Return the name of the service being checked."""
        return "Hasura GraphQL Engine"


class DjangoHealthChecks:
    """Check the health of the Django application's cache and database connections."""

    def __init__(self, *args, **kwargs):
        self.caches = getattr(settings, "CACHES", {})

    def get_database_status(self, *args, **kwargs) -> dict:
        """
        Check the status of the database connection(s). Returns a dictionary containing
        each connection's alias and its result for the ``is_usable()`` evaluation.
        """
        status = {}
        for connection in connections.all():
            try:
                if not connection.ensure_connection():
                    status[connection.alias] = True
            except OperationalError:  # pragma: no cover
                status[connection.alias] = False

        return status

    def get_cache_status(self, *args, **kwargs) -> dict:
        """
        Check the status of Django's cache configuration. Returns a dictionary containing
        each cache's alias and its result for a write test.
        """
        caches_aliases = self.caches.keys()
        value = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        status = {}
        for alias in caches_aliases:
            try:
                cache = django_caches[alias]
                cache.set("django_status_test_cache", value)
                status[alias] = True
            except:  # pragma: no cover
                status[alias] = False

        return status
