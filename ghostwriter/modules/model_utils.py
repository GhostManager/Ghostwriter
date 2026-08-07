"""This contains utilities for managing and converting models."""

# Standard Libraries
from itertools import chain
from typing import Optional, Type

# Django Imports
import django
from django.db import transaction
from django.db.models import ForeignKey, Q


def to_dict(instance: django.db.models.Model, include_id: bool = False, resolve_fk: bool = False) -> dict:
    """
    Converts a model instance to a dictionary with only the desirable field
    data. Extra fields provided by ``.__dict__``, like ``_state``, are removed.

    Ref: https://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact

    **Parameters**

    ``instance``
        Instance of ``django.db.models.Model``
    ``include_id``
        Whether to include the ``id`` field in the dictionary (Default: False)
    ``resolve_fk``
        Whether to resolve foreign key fields to an object (Default: False)
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        data[f.name] = f.value_from_object(instance)
        if isinstance(f, ForeignKey) and resolve_fk:
            fk_id = f.value_from_object(instance)
            data[f.name] = f.related_model.objects.get(id=fk_id)
    for f in opts.many_to_many:
        data[f.name] = [i.id for i in f.value_from_object(instance)]
    if not include_id:
        del data["id"]
    return data


def _clamp_position(position: int, count: int) -> int:
    """Return a one-based position that fits inside a group of findings."""
    if count < 1:
        return 1
    return min(max(position, 1), count)


def normalize_finding_positions(
    model: Type[django.db.models.Model],
    report_id: int,
    severity_id: int,
    moving_instance_id: Optional[int] = None,
    target_position: Optional[int] = None,
    skip_if_contiguous: bool = False,
) -> None:
    """
    Normalize the positions for one report and severity group.

    The report row lock serializes all ordering work for that report. The
    deterministic ``position, id`` order makes duplicate positions converge,
    while only writing rows whose position must change makes follow-up Hasura
    events no-ops.
    """
    report_model = model._meta.get_field("report").related_model
    with transaction.atomic():
        report_model.objects.select_for_update().get(id=report_id)
        _normalize_locked_finding_positions(
            model,
            report_id,
            severity_id,
            moving_instance_id,
            target_position,
            skip_if_contiguous,
        )


def _normalize_locked_finding_positions(
    model: Type[django.db.models.Model],
    report_id: int,
    severity_id: int,
    moving_instance_id: Optional[int] = None,
    target_position: Optional[int] = None,
    skip_if_contiguous: bool = False,
) -> None:
    """Normalize one severity group while the caller holds the report lock."""
    findings = list(
        model.objects.select_for_update()
        .filter(Q(report_id=report_id) & Q(severity_id=severity_id))
        .order_by("position", "id")
    )
    if not findings:
        return

    if skip_if_contiguous and all(
        finding.position == position
        for position, finding in enumerate(findings, start=1)
    ):
        return

    if moving_instance_id is not None:
        moving_finding = next(
            (finding for finding in findings if finding.id == moving_instance_id),
            None,
        )
        if moving_finding is not None:
            if target_position is None:
                target_position = len(findings)
            group_size = len(findings)
            findings = [
                finding for finding in findings if finding.id != moving_instance_id
            ]
            insert_at = _clamp_position(target_position, group_size) - 1
            findings.insert(insert_at, moving_finding)

    changed_findings = []
    for position, finding in enumerate(findings, start=1):
        if finding.position != position:
            finding.position = position
            changed_findings.append(finding)
    if changed_findings:
        model.objects.bulk_update(changed_findings, ["position"])


def set_finding_positions(
    instance: django.db.models.Model,
    old_pos: Optional[int],
    old_sev: Optional[int],
    new_pos: int,
    new_sev: int,
) -> None:
    """
    Updates the ``position`` value for a finding in a report. This is used when a finding is moved to a new position or
    changes severity.

    Ordering is serialized on the parent report row and only writes values
    that differ. This makes the Hasura events created by reordering converge
    instead of repeatedly reordering the same group.

    **Parameters**

    ``instance``
        Instance of :model:`reporting.ReportFindingLink`
    ``old_pos``
        The previous position assigned to the finding
    ``old_sev``
        The previous severity ID assigned to the finding
    ``new_pos``
        The new position assigned to the finding
    ``new_sev``
        The new severity ID assigned to the finding
    """
    if (
        old_pos is not None
        and old_sev is not None
        and old_pos == new_pos
        and old_sev == new_sev
    ):
        return None

    model = instance._meta.model
    report_model = model._meta.get_field("report").related_model
    report_id = instance.report_id

    with transaction.atomic():
        report_model.objects.select_for_update().get(id=report_id)
        # The event view obtains ``instance`` before this report lock. Reload
        # it after the lock so a queued event makes decisions using the state
        # committed by the event that ran immediately before it.
        instance.refresh_from_db()

        if old_pos is not None and old_sev is not None:
            # A later event can arrive after another event has already moved
            # the finding. Normalize the current state rather than replaying
            # that stale event's requested position.
            if instance.position != new_pos or instance.severity_id != new_sev:
                for severity_id in sorted(
                    {old_sev, new_sev, instance.severity_id}
                ):
                    _normalize_locked_finding_positions(
                        model,
                        report_id,
                        severity_id,
                    )
                return None

            if old_sev != new_sev:
                _normalize_locked_finding_positions(model, report_id, old_sev)

            _normalize_locked_finding_positions(
                model,
                report_id,
                new_sev,
                moving_instance_id=instance.id,
                target_position=new_pos,
            )
        else:
            # Existing behaviour: report findings added through GraphQL are
            # appended to their severity group regardless of input position.
            _normalize_locked_finding_positions(
                model,
                report_id,
                new_sev,
                moving_instance_id=instance.id,
                skip_if_contiguous=True,
            )
    return None
