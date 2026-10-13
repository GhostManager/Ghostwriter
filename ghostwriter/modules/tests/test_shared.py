"""Regression tests for shared import/export widgets."""

# Standard Libraries
from types import SimpleNamespace

# Django Imports
from django.test import SimpleTestCase

# 3rd Party Libraries
from taggit.models import Tag

# Ghostwriter Libraries
from ghostwriter.modules.shared import TagWidget
from ghostwriter.oplog.resources import OplogEntryResource
from ghostwriter.reporting.resources import FindingResource, ObservationResource
from ghostwriter.shepherd.resources import DomainResource, StaticServerResource


class TagWidgetTests(SimpleTestCase):
    """Preserve tag output when import/export supplies export context."""

    def test_none_value_with_export_context(self):
        widget = TagWidget(Tag, separator=",")

        self.assertEqual(widget.render(None, export_fields=["tags"], force_native_type=False), "")

    def test_shared_resources_export_selected_tags(self):
        resources = (FindingResource, ObservationResource, DomainResource, StaticServerResource, OplogEntryResource)
        for resource_class in resources:
            for names in ([], ["alpha"], ["alpha", "beta"]):
                with self.subTest(resource=resource_class.__name__, tags=names):
                    tags = [SimpleNamespace(name=name) for name in names]
                    obj = SimpleNamespace(tags=SimpleNamespace(all=lambda: tags))

                    dataset = resource_class().export([obj], export_fields=["tags"], force_native_type=False)

                    self.assertEqual(dataset.headers, ["tags"])
                    self.assertEqual(dataset[0], (",".join(names),))
