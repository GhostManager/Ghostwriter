"""This contains customizations for displaying the GraphQL application models in the admin panel."""

# Standard Libraries
import typing

# Django Imports
from django.contrib import admin, messages
from django.db import models
from django.http.request import HttpRequest

# Ghostwriter Libraries
from ghostwriter.api.models import AbstractAPIKey, APIKey


class APIKeyModelAdmin(admin.ModelAdmin):
    model: typing.Type[AbstractAPIKey]

    list_display = (
        "name",
        "created",
        "expiry_date",
        "_has_expired",
        "revoked",
    )
    list_filter = ("created",)
    search_fields = ("name",)

    def get_readonly_fields(self, request: HttpRequest, obj: models.Model = None) -> typing.Tuple[str, ...]:
        obj = typing.cast(AbstractAPIKey, obj)
        fields: typing.Tuple[str, ...]

        fields = ()
        if obj is not None and obj.revoked:
            fields = fields + ("name", "revoked", "expiry_date")

        return fields

    def save_model(
        self,
        request: HttpRequest,
        obj: AbstractAPIKey,
        form: typing.Any = None,
        change: bool = False,
    ) -> None:
        created = not obj.pk

        if created:
            _, token = self.model.objects.generate_token(obj)
            obj.token = token
            obj.save()
            message = f"The API key for {obj.name} is: " f"{token}"
            messages.add_message(request, messages.WARNING, message)
        else:
            obj.save()


admin.site.register(APIKey, APIKeyModelAdmin)
