"""This contains utilities for managing and converting models."""

# Standard Libraries
from itertools import chain

# Django Imports
import django
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


def set_finding_positions(
    instance: django.db.models.Model, old_pos: [int, None], old_sev: [int, None], new_pos: int, new_sev: int
) -> None:
    """
    Updates the ``position`` value for a finding in a report. This is used when a finding is moved to a new position or
    changes severity.

    The following adjustments use the queryset ``update()`` method (direct SQL statement) instead of calling ``save()``
    on the individual model instance. This avoids forever looping through position changes.

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
    # We don't import the model at the top of the file because it causes a circular import
    model = instance._meta.model

    if old_pos and old_sev:
        # Only run db queries if ``position`` or ``severity`` changed
        if old_pos != new_pos or old_sev != new_sev:
            # Get all findings in report that share the instance's severity rating
            finding_queryset = model.objects.filter(
                Q(report__pk=instance.report.pk) & Q(severity=instance.severity)
            ).order_by("position")

            # If severity rating changed, adjust positioning in the previous severity group
            if old_sev != new_sev:
                # Get a list of findings for the old severity rating
                old_sev_queryset = model.objects.filter(
                    Q(report__pk=instance.report.pk) & Q(severity=old_sev)
                ).order_by("position")
                if old_sev_queryset:
                    for finding in old_sev_queryset:
                        # Adjust position to close gap created by moved finding
                        if finding.position > old_pos:
                            new_pos = finding.position - 1
                            old_sev_queryset.filter(id=finding.id).order_by("position").update(position=new_pos)

            # The ``modelUpdateForm`` sets minimum number to 0, but check again for funny business
            instance.position = max(instance.position, 1)

            # The ``position`` value should not be larger than total findings
            if instance.position > finding_queryset.count():
                finding_queryset.filter(id=instance.id).update(position=finding_queryset.count())

            counter = 1
            if finding_queryset:
                # Loop from top position down and look for a match
                for finding in finding_queryset:
                    # Check if finding in loop is the finding being updated
                    if not instance.pk == finding.pk:
                        # Increment position counter when counter equals new value
                        if instance.position == counter:
                            counter += 1
                        finding_queryset.filter(id=finding.id).update(position=counter)
                        counter += 1
                    else:
                        pass
            # No other findings with the chosen severity, so set ``position`` to ``1``
            else:
                instance.position = 1
    # Place newly created findings at the end of the current list
    else:
        finding_queryset = model.objects.filter(Q(report__pk=instance.report.pk) & Q(severity=instance.severity))
        finding_queryset.filter(id=instance.id).update(position=finding_queryset.count())
    return None
