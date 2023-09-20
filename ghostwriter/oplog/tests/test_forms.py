# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    UserFactory,
)
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.oplog.forms import OplogEntryForm, OplogForm

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class OplogFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        name=None,
        project_id=None,
        **kwargs,
    ):
        return OplogForm(
            user=user,
            data={
                "name": name,
                "project": project_id,
            },
        )

    def test_valid_data(self):
        project = ProjectFactory()
        oplog = OplogFactory.build(project=project)
        form = self.form_data(user=self.user, **oplog.__dict__)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors.as_data()["project"][0].code == "invalid_choice")

        ProjectAssignmentFactory(operator=self.user, project=project)
        form = self.form_data(user=self.user, **oplog.__dict__)
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
        oplog_kwarg=None,
        instance=None,
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
            oplog=oplog_kwarg,
            instance=instance,
        )

    def test_valid_data(self):
        entry = OplogEntryFactory.build()
        form = self.form_data(**to_dict(entry), oplog_kwarg=self.oplog)
        self.assertTrue(form.is_valid())

    def test_valid_update_data(self):
        entry = OplogEntryFactory.create()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        entry = OplogEntryFactory.create()
        start_date = entry.start_date
        entry.start_date = None
        entry.end_date = None
        entry.save()
        entry.refresh_from_db()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())

        entry.start_date = start_date
        entry.save()
        entry.refresh_from_db()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())
