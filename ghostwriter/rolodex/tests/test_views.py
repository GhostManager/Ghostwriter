# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ProjectScopeFactory,
    StaticServerFactory,
)
from ghostwriter.rolodex.templatetags import determine_primary

logging.disable(logging.INFO)

PASSWORD = "SuperNaturalReporting!"


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectObjective = ProjectObjectiveFactory._meta.model
        cls.project = ProjectFactory()
        for x in range(3):
            ProjectObjectiveFactory(project=cls.project)

        cls.server = StaticServerFactory()
        cls.aux_address_1 = AuxServerAddressFactory(
            static_server=cls.server, ip_address="1.1.1.1", primary=True
        )
        cls.aux_address_2 = AuxServerAddressFactory(
            static_server=cls.server, ip_address="1.1.1.2", primary=False
        )

        cls.scope = ProjectScopeFactory(
            project=cls.project,
            scope="1.1.1.1\r\n1.1.1.2\r\n1.1.1.3\r\n1.1.1.4\r\n1.1.1.5",
        )

    def setUp(self):
        pass

    def test_tags(self):
        queryset = self.ProjectObjective.objects.all()

        obj_dict = determine_primary.group_by_priority(queryset)
        self.assertEqual(len(obj_dict), 3)

        for group in obj_dict:
            self.assertEqual(
                determine_primary.get_item(obj_dict, group), obj_dict.get(group)
            )

        future_date = date.today() + timedelta(days=10)
        self.assertEqual(determine_primary.plus_days(date.today(), 10), future_date)
        self.assertEqual(determine_primary.days_left(future_date), 10)

        self.assertEqual(determine_primary.get_primary_address(self.server), "1.1.1.1")

        self.assertEqual(
            determine_primary.get_scope_preview(self.scope.scope, 5),
            "1.1.1.1\n1.1.1.2\n1.1.1.3\n1.1.1.4\n1.1.1.5",
        )
        self.assertEqual(
            determine_primary.get_scope_preview(self.scope.scope, 2), "1.1.1.1\n1.1.1.2"
        )
