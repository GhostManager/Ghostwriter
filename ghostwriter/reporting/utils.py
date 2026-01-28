"""Utility functions for the Reporting application."""

# Standard Libraries
import logging

# 3rd Party Libraries
import yaml

# Ghostwriter Libraries
from ghostwriter.reporting.models import Acronym

logger = logging.getLogger(__name__)


def import_acronyms_from_yaml(yaml_content, override=False, user=None):
    """
    Import acronyms from YAML content.

    Args:
        yaml_content (str): YAML content to parse
        override (bool): Whether to update existing acronyms
        user: User performing the import (for created_by field)

    Returns:
        dict: Statistics about the import (created, updated, skipped)

    Raises:
        ValueError: If YAML is invalid or has wrong structure
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {str(e)}")

    if not isinstance(data, dict):
        raise ValueError("YAML must contain a dictionary of acronyms")

    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    for acronym_text, expansions in data.items():
        if not isinstance(expansions, list):
            stats["errors"].append(
                f"Acronym '{acronym_text}' must have a list of expansions"
            )
            continue

        # Process each expansion with priority based on order
        for index, expansion_data in enumerate(expansions):
            if not isinstance(expansion_data, dict):
                stats["errors"].append(
                    f"Each expansion for '{acronym_text}' must be a dictionary"
                )
                continue

            if "full" not in expansion_data:
                stats["errors"].append(
                    f"Expansion for '{acronym_text}' missing 'full' field"
                )
                continue

            expansion_text = expansion_data["full"]

            # Higher priority for earlier entries (reverse index)
            priority = len(expansions) - index

            # Check if acronym with this expansion already exists
            existing = Acronym.objects.filter(
                acronym=acronym_text, expansion=expansion_text
            ).first()

            if existing:
                if override:
                    existing.priority = priority
                    existing.save()
                    stats["updated"] += 1
                    logger.info(f"Updated acronym: {acronym_text} → {expansion_text}")
                else:
                    stats["skipped"] += 1
                    logger.debug(
                        f"Skipped existing acronym: {acronym_text} → {expansion_text}"
                    )
            else:
                # If override is True, deactivate all other entries for this acronym first
                if override:
                    Acronym.objects.filter(acronym=acronym_text).update(is_active=False)

                Acronym.objects.create(
                    acronym=acronym_text,
                    expansion=expansion_text,
                    priority=priority,
                    created_by=user,
                    is_active=True,
                )
                stats["created"] += 1
                logger.info(f"Created acronym: {acronym_text} → {expansion_text}")

    return stats
