
from typing import Any
from datetime import datetime, timezone, timedelta

from django.views.generic.detail import DetailView
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from django.db.models import Model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import requires_csrf_token

from ghostwriter.api.utils import (
    COLLAB_FINDING_ID_CLAIM,
    COLLAB_JWT_TYPE,
    COLLAB_MODEL_CLAIM,
    COLLAB_NO_ID,
    COLLAB_OBJECT_ID_CLAIM,
    COLLAB_REPORT_ID_CLAIM,
    RoleBasedAccessControlMixin,
    generate_jwt,
)
from ghostwriter.commandcenter.models import ExtraFieldSpec, ReportConfiguration
from ghostwriter.modules.custom_serializers import ExtraFieldsSpecSerializer

COLLAB_MODEL_NAME_MAP = {
    "reportfindinglink": "report_finding_link",
    "reportobservationlink": "report_observation_link",
}

# Ensure a CSRF token is available for JS code that makes use of it.
@method_decorator(requires_csrf_token, name="dispatch")
class CollabModelUpdate(RoleBasedAccessControlMixin, DetailView):
    """
    Base view for collaborative forms.

    See `/collab-server/how-to-collab.md` for more info.
    """

    # Default template. Subclasses will likely want to extend this template.
    template_name = "collab_editing/update.html"

    # Route to redirect to when authorization fails
    unauthorized_redirect = "home:dashboard"

    # If set, also adds the extra fields for the model
    has_extra_fields: bool | type[Model] = True

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to edit " + self.model._meta.verbose_name_plural + ".")
        return redirect(self.unauthorized_redirect)

    @property
    def collab_editing_script_path(self) -> str:
        return "assets/collab_forms_{}.js".format(self.model._meta.model_name)

    def collab_model_name(self) -> str:
        model_name = self.model._meta.model_name
        return COLLAB_MODEL_NAME_MAP.get(model_name, model_name)

    @staticmethod
    def collab_jwt_claims(model_name, obj):
        report_id = COLLAB_NO_ID
        finding_id = COLLAB_NO_ID

        if model_name == "report":
            report_id = obj.pk
        elif model_name == "report_finding_link":
            report_id = obj.report_id or COLLAB_NO_ID
            finding_id = obj.pk
        elif model_name == "report_observation_link":
            report_id = obj.report_id or COLLAB_NO_ID

        return {
            COLLAB_MODEL_CLAIM: model_name,
            COLLAB_OBJECT_ID_CLAIM: obj.pk,
            COLLAB_REPORT_ID_CLAIM: report_id,
            COLLAB_FINDING_ID_CLAIM: finding_id,
        }

    @staticmethod
    def context_data(user, obj_id, extra_fields=None, collab_claims=None):
        report_config = ReportConfiguration.get_solo()
        if collab_claims is None:
            collab_claims = {
                COLLAB_MODEL_CLAIM: "",
                COLLAB_OBJECT_ID_CLAIM: obj_id or COLLAB_NO_ID,
                COLLAB_REPORT_ID_CLAIM: COLLAB_NO_ID,
                COLLAB_FINDING_ID_CLAIM: COLLAB_NO_ID,
            }
        return {
            "collab_user": user,
            "collab_jwt": generate_jwt(
                user,
                exp=datetime.now(timezone.utc) + timedelta(hours=24),
                token_type=COLLAB_JWT_TYPE,
                extra_claims=collab_claims,
            )[1],
            "collab_model_id": obj_id,
            "collab_media_url": settings.MEDIA_URL,
            "collab_extra_fields_spec_ser":
                ExtraFieldsSpecSerializer(extra_fields, many=True).data if extra_fields is not None else None,
            "collab_default_cvss_version": report_config.default_cvss_version,
        }

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        extra_fields = None
        if self.has_extra_fields:
            if self.has_extra_fields is True:
                extra_fields_model = self.model
            else:
                extra_fields_model = self.has_extra_fields
            extra_fields = ExtraFieldSpec.for_model(extra_fields_model)
        context.update(self.context_data(
            self.request.user,
            self.object.pk,
            extra_fields,
            self.collab_jwt_claims(self.collab_model_name(), self.object),
        ))
        context["model_name"] = self.model._meta.model_name
        context["collab_editing_script_path"] = self.collab_editing_script_path
        return context
