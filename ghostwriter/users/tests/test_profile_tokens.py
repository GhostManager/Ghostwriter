# Standard Libraries
import logging
from datetime import timedelta
from http import HTTPStatus

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.models import (
    APIKey,
    ServicePrincipal,
    ServiceToken,
    ServiceTokenPreset,
)
from ghostwriter.factories import (
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class UserProfileTokenDisplayTests(TestCase):
    """Tests for token display behavior on the user profile page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_token_tables_style_expiry_dates_and_filter_expired_rows(self):
        soon = timezone.now() + timedelta(days=1)
        later = timezone.now() + timedelta(days=8)
        expired = timezone.now() - timedelta(days=1)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=self.user
        )

        APIKey.objects.create_token(
            user=self.user,
            name="Expiring API Token",
            expiry_date=soon,
        )
        APIKey.objects.create_token(
            user=self.user,
            name="Later API Token",
            expiry_date=later,
        )
        APIKey.objects.create_token(
            user=self.user,
            name="Expired API Token",
            expiry_date=expired,
        )
        ServiceToken.objects.create_token(
            name="Expiring Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=soon,
        )
        ServiceToken.objects.create_token(
            name="Later Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=later,
        )
        ServiceToken.objects.create_token(
            name="Expired Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=expired,
        )

        response = self.client_auth.get(self.uri)

        self.assertContains(response, 'id="api-token-card"')
        self.assertContains(response, 'id="service-token-card"')
        self.assertContains(
            response,
            "API tokens authenticate as your user account and inherit your current Ghostwriter permissions.",
        )
        self.assertContains(
            response,
            "Service tokens authenticate as non-human service principals",
        )
        self.assertContains(response, "use only the permissions assigned to the token")
        self.assertContains(response, 'id="js-hide-expired"')
        self.assertContains(response, 'id="js-hide-expired-service-tokens"')
        self.assertContains(
            response, 'data-expired-token-selector=".js-expired-api-token"'
        )
        self.assertContains(
            response, 'data-expired-token-selector=".js-expired-service-token"'
        )
        self.assertContains(response, 'data-storage-key="profileHideExpiredApiTokens"')
        self.assertContains(
            response, 'data-storage-key="profileHideExpiredServiceTokens"'
        )
        self.assertContains(response, "localStorage.getItem(storageKey)")
        self.assertContains(response, "localStorage.setItem(storageKey")
        self.assertContains(
            response,
            'class="align-middle text-left warning"',
            count=2,
        )
        self.assertContains(response, "Later API Token")
        self.assertContains(response, "Later Service Token")
        self.assertContains(
            response,
            'class="align-middle text-left burned js-expired-token js-expired-api-token"',
        )
        self.assertContains(
            response,
            'class="align-middle text-left burned js-expired-token js-expired-service-token"',
        )
        self.assertContains(response, 'data-revoke-target-preview="Expired API Token"')
        self.assertContains(
            response, 'data-revoke-target-preview="Expired Service Token"'
        )
        self.assertContains(
            response,
            'data-revoke-target-url="/api/ajax/token/revoke/',
        )
        self.assertContains(
            response,
            'data-revoke-target-url="/api/ajax/service-token/revoke/',
        )
        self.assertContains(response, "Edit Expiry", count=6)
        self.assertContains(response, 'id="edit-token-expiry-modal"')
        self.assertContains(response, 'data-expiry-target-url="/api/token/expiry/')
        self.assertContains(
            response,
            'data-expiry-target-url="/api/service-token/expiry/',
        )
        self.assertContains(response, 'data-expiry-regenerates-token="true"', count=3)
        self.assertContains(response, 'data-expiry-regenerates-token="false"', count=3)
        self.assertContains(response, "Choose a future date and time.")
        self.assertContains(
            response, "Changing an API token's expiry generates a replacement token."
        )
        self.assertContains(response, "$(event.relatedTarget)")
        self.assertContains(response, "edit-token-expiry-regeneration-warning")
        self.assertContains(response, "$modal.data('revoke-target', $target)")

    def test_profile_lazy_loads_service_token_details(self):
        project = ProjectFactory(codename="Alpha Project")
        other_project = ProjectFactory(codename="Bravo Project")
        ProjectAssignmentFactory(project=project, operator=self.user)
        ProjectAssignmentFactory(project=other_project, operator=self.user)
        oplog = OplogFactory(name="Operator Activity", project=project)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=self.user
        )
        project_token, _ = ServiceToken.objects.create_token(
            name="Project Reader",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[project.id, other_project.id],
            ),
        )
        oplog_token, _ = ServiceToken.objects.create_token(
            name="Oplog Writer",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.OPLOG_RW,
                oplog_id=oplog.id,
            ),
        )

        response = self.client_auth.get(self.uri)

        self.assertNotContains(
            response, '<th class="align-middle text-left">Service Principal</th>'
        )
        self.assertNotContains(
            response, '<th class="align-middle text-left">Scope</th>'
        )
        self.assertContains(
            response,
            f'data-details-url="/api/ajax/service-token/details/{project_token.id}"',
        )
        self.assertContains(
            response,
            f'data-details-url="/api/ajax/service-token/details/{oplog_token.id}"',
        )
        self.assertContains(response, 'id="service-token-details-modal"', count=1)
        self.assertContains(response, 'id="service-token-details-modal-content"')
        self.assertContains(response, "$.ajax({")
        self.assertNotContains(
            response, f'id="service-token-details-modal-{project_token.id}"'
        )
        self.assertNotContains(
            response, f'id="service-token-details-modal-{oplog_token.id}"'
        )
        self.assertNotContains(response, "External Integration")
        self.assertNotContains(response, "Operator Activity")
        self.assertNotContains(
            response, "This token reads only the selected projects listed below."
        )
        self.assertNotContains(response, "Read oplog and entries")

    def test_service_token_details_view_lists_project_access(self):
        project = ProjectFactory(codename="Alpha Project")
        other_project = ProjectFactory(codename="Bravo Project")
        ProjectAssignmentFactory(project=project, operator=self.user)
        ProjectAssignmentFactory(project=other_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=self.user
        )
        project_token, _ = ServiceToken.objects.create_token(
            name="Project Reader",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[project.id, other_project.id],
            ),
        )

        response = self.client_auth.get(
            reverse("api:ajax_service_token_details", kwargs={"pk": project_token.id})
        )

        self.assertContains(response, "Project Reader Access Details")
        self.assertContains(response, "Service Principal")
        self.assertContains(response, "External Integration")
        self.assertContains(response, "Access Summary")
        self.assertContains(
            response, "This token reads only the selected projects listed below."
        )
        self.assertNotContains(
            response, "This token does not have oplog-specific access."
        )
        self.assertContains(response, "ALPHA PROJECT")
        self.assertContains(response, "BRAVO PROJECT")
        self.assertContains(
            response,
            "This token has no direct oplog assignment. It can access logs under the above projects.",
        )

    def test_service_token_details_view_lists_oplog_access(self):
        project = ProjectFactory(codename="Alpha Project")
        ProjectAssignmentFactory(project=project, operator=self.user)
        oplog = OplogFactory(name="Operator Activity", project=project)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=self.user
        )
        oplog_token, _ = ServiceToken.objects.create_token(
            name="Oplog Writer",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.OPLOG_RW,
                oplog_id=oplog.id,
            ),
        )

        response = self.client_auth.get(
            reverse("api:ajax_service_token_details", kwargs={"pk": oplog_token.id})
        )

        self.assertContains(response, "Oplog Writer Access Details")
        self.assertContains(response, "Service Principal")
        self.assertContains(response, "External Integration")
        self.assertContains(response, "Access Summary")
        self.assertContains(
            response, "This token does not have project-wide read access."
        )
        self.assertNotContains(
            response, "This token does not have oplog-specific access."
        )
        self.assertContains(response, "Operator Activity")
        self.assertContains(response, "Read oplog and entries")
        self.assertContains(response, "Create entries")
        self.assertContains(response, "Update entries")
        self.assertContains(response, "Delete entries")

    def test_service_token_details_view_rejects_tokens_owned_by_other_users(self):
        other_user = UserFactory(password=PASSWORD)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=other_user
        )
        token, _ = ServiceToken.objects.create_token(
            name="Other User Token",
            created_by=other_user,
            service_principal=principal,
        )

        response = self.client_auth.get(
            reverse("api:ajax_service_token_details", kwargs={"pk": token.id})
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
