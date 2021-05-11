"""This contains all of the custom `crispy_forms.layout.LayoutObject` objects used by Ghostwriter."""

# Django Imports
from django.template.loader import render_to_string

# 3rd Party Libraries
from crispy_forms.bootstrap import Container
from crispy_forms.layout import TEMPLATE_PACK, Field, LayoutObject


class Formset(LayoutObject):
    """
    Custom ``Formset()`` object for use with ``crispy_forms`` forms.

    **Template**

    :template:`formset.html`
    """

    # Default form used for rendering the formset
    template = "formset.html"
    # A name for the formset object that can be used in the template
    # e.g., "Add {{ object_name }}" to insert "Add Objective"
    object_context_name = "Another"

    def __init__(
        self,
        formset_context_name,
        template=None,
        helper_context_name=None,
        object_context_name=None,
    ):
        self.formset_context_name = formset_context_name
        self.helper_context_name = helper_context_name
        if object_context_name:
            self.object_context_name = object_context_name
        if template:
            self.template = template
        # crispy_forms/layout.py:302 requires us to have a fields property
        self.fields = []

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        formset = context.get(self.formset_context_name)
        helper = context.get(self.helper_context_name)
        object_name = self.object_context_name

        # Form closes prematurely if this isn't explicitly stated
        if helper:
            helper.form_tag = False
        context.update({"formset": formset, "helper": helper, "object_name": object_name})
        return render_to_string(self.template, context.flatten())


class CustomTab(Container):
    """
    Custom version of the ``Tab()`` object for use with ``crispy_forms`` forms ``TabHolder()``.

    Wraps fields in a div whose default class is "tab-pane" and takes a name as first argument.

    Replaces ``Tab()`` from:
        crispy_forms/bootstrap.py#L275

    **Template**

    :template:`tab-link.html`
    """

    # Default form used for rendering the formset
    link_template = "tab-link.html"
    # Default CSS class for the tab pane
    css_class = "tab-pane"
    # Custom CSS for the ``nav-link`` element
    # link_css_class = ""

    def __init__(self, name, *fields, **kwargs):
        super().__init__(*fields, **kwargs)
        self.name = name
        self.fields = list(fields)
        self.link_css_class = kwargs.get("link_css_class", None)

    def render_link(self, template_pack=TEMPLATE_PACK, **kwargs):
        """
        Render the link for the tab-pane. It must be called after ``render()`` so
        ``css_class`` is updated with active if needed.
        """
        link_template = self.link_template
        return render_to_string(link_template, {"link": self})


class SwitchToggle(Field):
    """
    Custom ``Field()`` object for use with ``crispy_forms`` forms. This object transforms
    a checkbox into a toggle switch.

    **Template**

    :template:`switch.html`
    """

    template = "switch.html"

    def __init__(self, field, *args, **kwargs):
        super().__init__(field, *args, **kwargs)
