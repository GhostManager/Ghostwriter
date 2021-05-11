# Django Imports
from django import template
from django.utils.translation import gettext_lazy as _

try:
    from django.apps import apps  # noqa isort:skip

    get_model = apps.get_model
except ImportError:
    from django.db.models.loading import get_model  # noqa isort:skip


register = template.Library()


@register.simple_tag()
def get_solo(model_path):
    try:
        app_label, model_name = model_path.rsplit(".", 1)
    except ValueError:
        raise template.TemplateSyntaxError(
            _(
                "Templatetag requires the model dotted path: 'app_label.ModelName'. "
                "Received '%s'." % model_path
            )
        )
    model_class = get_model(app_label, model_name)
    if not model_class:
        raise template.TemplateSyntaxError(
            _(
                "Could not get the model name '%(model)s' from the application "
                "named '%(app)s'"
                % {
                    "model": model_name,
                    "app": app_label,
                }
            )
        )
    return model_class.get_solo()
