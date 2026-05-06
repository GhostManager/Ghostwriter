# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.factories import UserFactory

logging.disable(logging.CRITICAL)


class CollabModelUpdateTests(TestCase):
    """Collection of tests for collaborative model update views."""

    def test_context_data_uses_collab_jwt_type(self):
        user = UserFactory()

        context = CollabModelUpdate.context_data(user, obj_id=1)

        self.assertEqual(
            utils.get_jwt_type(context["collab_jwt"]), utils.COLLAB_JWT_TYPE
        )
