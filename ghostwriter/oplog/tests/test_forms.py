# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import OplogEntryFactory, OplogFactory, ProjectFactory
from ghostwriter.oplog.forms import OplogEntryForm, OplogForm

logging.disable(logging.INFO)

PASSWORD = "SuperNaturalReporting!"


class OplogFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        project_id=None,
        **kwargs,
    ):
        return OplogForm(
            data={
                "name": name,
                "project": project_id,
            },
        )

    def test_valid_data(self):
        project = ProjectFactory()
        oplog = OplogFactory.build(project=project)
        form = self.form_data(**oplog.__dict__)
        self.assertTrue(form.is_valid())


class OplogEntryFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogEntryForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.oplog = OplogFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        oplog_id=None,
        start_date=None,
        end_date=None,
        source_ip=None,
        dest_ip=None,
        tool=None,
        user_context=None,
        command=None,
        description=None,
        output=None,
        comments=None,
        operator_name=None,
        **kwargs,
    ):
        return OplogEntryForm(
            data={
                "oplog_id": oplog_id,
                "start_date": start_date,
                "end_date": end_date,
                "source_ip": source_ip,
                "dest_ip": dest_ip,
                "tool": tool,
                "user_context": user_context,
                "command": command,
                "description": description,
                "output": output,
                "comments": comments,
                "operator_name": operator_name,
            },
        )

    def test_valid_data(self):
        entry = OplogEntryFactory.build()
        form = self.form_data(**entry.__dict__, oplog_id=self.oplog.id)
        self.assertTrue(form.is_valid())
