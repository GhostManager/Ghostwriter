"""This contains shared model resources used by multiple applications."""

# Standard Libraries
from urllib.parse import quote

# 3rd Party Libraries
from import_export import widgets
from import_export.fields import Field
from taggit.forms import TagField
from taggit.models import Tag

# The following is based on the following StackOverflow answer:
# https://stackoverflow.com/questions/59582619/how-to-import-django-taggit-tag-in-django-import-export


class TagWidget(widgets.ManyToManyWidget):
    def render(self, value, obj=None):
        if value is None:
            return ""
        return self.separator.join([obj.name for obj in value.all()])

    def clean(self, value, row=None, *args, **kwargs):
        values = TagField().clean(value)
        return [Tag.objects.get_or_create(name=tag)[0] for tag in values]


class TagFieldImport(Field):
    def save(self, obj, data, is_m2m=False):
        if not self.readonly:
            attrs = self.attribute.split("__")
            for attr in attrs[:-1]:
                obj = getattr(obj, attr, None)
            cleaned = self.clean(data)
            if cleaned is not None or self.saves_null_values:
                if not is_m2m:
                    setattr(obj, attrs[-1], cleaned)
                else:
                    getattr(obj, attrs[-1]).set(cleaned, clear=True)


def taggit_before_import_row(row):
    """Check if the ``tags`` field is empty and set it to a comma (nothing) if it is."""
    # The ``django-import-export`` app looks at the ``tags`` field to determine if the field can be null or blank
    # and will throw an error if it is not. The field doesn't have Django's ``null`` attribute set to ``True``
    # so imports will fail. ``TaggableManager`` doesn't set that attribute so this is a workaround to set the field to a
    # comma if it is null. A comma is effectively null for the purposes of this application.
    if "tags" in row.keys():
        # A blank field may be blank ("") or ``None`` depending on the import file format.
        if row["tags"] == "" or row["tags"] is None:
            row["tags"] = ","


def add_content_disposition_header(response, filename):
    """
    Add an RFC5987 / RFC6266 compliant `Content-Disposition` header to an
    `HttpResponse` to tell the browser to save the HTTP response to a file.
    """
    try:
        filename.encode("ascii")
        file_expr = 'filename="{}"'.format(filename)
    except UnicodeEncodeError:
        file_expr = "filename*=utf-8''{}".format(quote(filename))
    response["Content-Disposition"] = "attachment; {}".format(file_expr)
    return response


def search_tags(queryset, value):
    """Filter a queryset by tags."""
    # There is no case-insensitive version of `in` for Django ORM, so we use `iregex` instead.
    return queryset.filter(tags__name__iregex=r"(" + value + ")").distinct()
