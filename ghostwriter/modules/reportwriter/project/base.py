
from ghostwriter.modules.custom_serializers import FullProjectSerializer
from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base.base import ExportBase


class ExportProjectBase(ExportBase):
    """
    Mixin class for exporting projects.

    Provides a `serialize_object` implementation for serializing the `Project` database object,
    and helper functions for creating Jinja contexts.
    """

    def serialize_object(self, object):
        return FullProjectSerializer(object).data

    def jinja_richtext_base_context(self) -> dict:
        """
        Generates a Jinja context for use in rich text fields
        """
        base_context = {
            # `{{.foo}}` converts to `{{obsolete.foo}}`
            "_old_dot_vars": {
                "client": self.data["client"]["short_name"] or self.data["client"]["name"],
                "project_start": self.data["project"]["start_date"],
                "project_end": self.data["project"]["end_date"],
                "project_type": self.data["project"]["type"].lower(),
            },
            "mk_caption": jinja_funcs.caption,
            "mk_ref": jinja_funcs.ref,
        }
        base_context.update(self.data)
        return base_context
