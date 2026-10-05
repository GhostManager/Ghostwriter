"""Persist the latest background health-check result across web processes."""

# Django Imports
from django.db import models


class DashboardHealthSnapshot(models.Model):
    """One shared summary and creation lock; monitoring replaces initial UNKNOWN."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    checked_at = models.DateTimeField()
    summary = models.JSONField(default=dict)
