
from typing import Any

from django.views.generic.detail import DetailView
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from django.db.models import Model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import requires_csrf_token

from ghostwriter.api.utils import RoleBasedAccessControlMixin, generate_jwt
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import ExtraFieldsSpecSerializer

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

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["model_name"] = self.model._meta.model_name
        context["jwt"] = generate_jwt(self.request.user)[1]
        context["media_url"] = settings.MEDIA_URL
        context["collab_editing_script_path"] = self.collab_editing_script_path
        if self.has_extra_fields:
            if self.has_extra_fields is True:
                extra_fields_model = self.model
            else:
                extra_fields_model = self.has_extra_fields
            context["extra_fields_spec_ser"] = ExtraFieldsSpecSerializer(
                ExtraFieldSpec.for_model(extra_fields_model), many=True
            ).data
        return context
