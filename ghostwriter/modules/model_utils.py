"""This contains utilities for managing and converting models."""

# Standard Libraries
from itertools import chain

# Django Imports
import django
from django.db.models import ForeignKey


def to_dict(instance: django.db.models.Model, include_id: bool = False, resolve_fk: bool = False) -> dict:
    """
    Converts a model instance to a dictionary with only the desirable field
    data. Extra fields provided by ``.__dict__``, like ``_state``, are removed.

    Ref: https://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact

    **Parameters**

    ``instance``
        Instance of ``django.db.models.Model``
    ``include_id``
        Whether or not to include the ``id`` field in the dictionary (Default: False)
    ``resolve_fk``
        Whether or not to resolve foreign key fields to an object (Default: False)
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
