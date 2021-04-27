# Django Imports
from django.test import TestCase

from .factories import FindingFactory


class FindingModelsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.Finding = FindingFactory._meta.model

    def test_crud_finding(self):
        # Create
        finding = FindingFactory(title="Awful Finding")

        # Read
        self.assertEqual(finding.title, "Awful Finding")
        self.assertEqual(finding.pk, finding.id)
        self.assertQuerysetEqual(
            self.Finding.objects.all(), ["<Finding: [None] Awful Finding>"]
        )

        # Update
        finding.title = "Not so Bad Finding"
        finding.save()
        self.assertQuerysetEqual(
            self.Finding.objects.all(), ["<Finding: [None] Not so Bad Finding>"]
        )

        # Delete
        finding.title = "Not so Bad Finding"
        finding.delete()
        assert not self.Finding.objects.all().exists()
