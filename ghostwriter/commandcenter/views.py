
import logging
from typing import Any
from datetime import datetime, timezone, timedelta

from django.views import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.db.models import Model
from django.utils.decorators import method_decorator
from django.utils.html import escape
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
from ghostwriter.commandcenter.templatetags.extra_fields import _expand_evidence_and_sanitize
from ghostwriter.modules.custom_serializers import ExtraFieldsSpecSerializer
from ghostwriter.modules.reportwriter.base import ReportExportError, ReportExportTemplateError

logger = logging.getLogger(__name__)

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
                COLLAB_OBJECT_ID_CLAIM: (
                    obj_id if obj_id is not None else COLLAB_NO_ID
                ),
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


class ExtraFieldJsonView(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return one JSON extra field value for a model instance.

    Subclasses must set ``model`` and route with ``pk`` and ``extra_field_name``.
    """

    def test_func(self):
        obj = self.get_object()
        can_view = getattr(obj, "user_can_view", None)
        if callable(can_view):
            return can_view(self.request.user)
        return self.request.user.is_active

    def handle_no_permission(self):
        return JsonResponse(
            {
                "result": "error",
                "message": "You do not have permission to access that.",
            },
            status=403,
        )

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        field = get_object_or_404(
            ExtraFieldSpec.for_model(self.model),
            internal_name=kwargs["extra_field_name"],
            type="json",
        )
        return JsonResponse(
            {
                "field": field.display_name,
                "value": field.value_of(obj.extra_fields),
            }
        )



class ExtraFieldRichTextPreviewView(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return rendered rich-text HTML for an extra field, with Jinja2 template
    variables resolved using the same export context used for report generation.

    Subclasses must set ``model`` and may override ``build_exporter`` and
    ``extract_rendered_field`` to customize context building.
    """

    def test_func(self):
        obj = self.get_object()
        can_view = getattr(obj, "user_can_view", None)
        if callable(can_view):
            return can_view(self.request.user)
        return self.request.user.is_active

    def handle_no_permission(self):
        return HttpResponse(
            '<div class="alert alert-danger" role="alert">'
            "You do not have permission to access that.</div>",
            content_type="text/html",
            status=403,
        )

    #: Model used to look up ``ExtraFieldSpec`` entries.  Defaults to
    #: ``self.model`` but can be overridden when the specs are registered
    #: against a different model (e.g. ``Finding`` for ``ReportFindingLink``).
    extra_field_spec_model = None

    def build_exporter(self, obj):
        """
        Return an ``ExportBase`` subclass instance whose ``map_rich_texts``
        method produces ``LazilyRenderedTemplate`` objects for rich-text
        extra fields.

        The default implementation raises ``NotImplementedError``.
        """
        raise NotImplementedError

    def extract_rendered_field(self, exporter, base_context, field_name):
        """
        Navigate the processed *base_context* to find the rendered value of
        *field_name*.  Returns an HTML string.

        The default walks ``base_context["extra_fields"][field_name]``.
        """
        value = base_context.get("extra_fields", {}).get(field_name)
        if value is None:
            return ""
        return str(value.__html__()) if hasattr(value, "__html__") else str(value)

    def get_report_for_evidence(self, obj):
        """Return a ``Report`` instance to use for evidence expansion, or ``None``."""
        return None

    def get_client(self, obj):
        """Return the :model:`rolodex.Client` for image resolution, or ``None``."""
        return None

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        field_name = kwargs["extra_field_name"]

        spec_model = self.extra_field_spec_model or self.model
        get_object_or_404(
            ExtraFieldSpec.for_model(spec_model),
            internal_name=field_name,
            type="rich_text",
        )

        try:
            exporter = self.build_exporter(obj)
            base_context = exporter.map_rich_texts()
            html = self.extract_rendered_field(exporter, base_context, field_name)
        except ReportExportTemplateError as error:
            logger.warning(
                "Template error rendering rich-text preview for %s field %s: %s",
                self.model.__name__,
                field_name,
                error,
            )
            return HttpResponse(
                '<div class="alert alert-danger" role="alert">'
                "<strong>Template Error</strong><br>"
                f"{escape(str(error))}"
                "</div>",
                content_type="text/html",
                status=200,
            )
        except ReportExportError as error:
            logger.warning(
                "Export error rendering rich-text preview for %s field %s: %s",
                self.model.__name__,
                field_name,
                error,
            )
            return HttpResponse(
                '<div class="alert alert-danger" role="alert">'
                "<strong>Preview Error</strong><br>"
                f"{escape(str(error))}</div>",
                content_type="text/html",
                status=200,
            )

        report = self.get_report_for_evidence(obj)
        client = self.get_client(obj)
        sanitized = _expand_evidence_and_sanitize(html, report, client=client)
        return HttpResponse(sanitized, content_type="text/html")
