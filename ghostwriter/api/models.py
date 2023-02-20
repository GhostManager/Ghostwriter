"""This contains all the database models used by the GraphQL application."""

# Standard Libraries
import typing

# Django Imports
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.utils import generate_jwt, jwt_decode_no_verification

User = get_user_model()


class BaseAPIKeyManager(models.Manager):
    """
    Baseline API key manager used for ``APIKeyManager``.

    Code is adapted from the ``djangorestframework-api-key`` package by florimondmanca.
    """

    def generate_token(self, obj: "AbstractAPIKey") -> str:
        # Generate JWT with requested expiration date instead of default of +15m
        payload, token = generate_jwt(obj.user, exp=obj.expiry_date)
        obj.token = token
        return payload, token

    def create_token(self, **kwargs: typing.Any) -> typing.Tuple["AbstractAPIKey", str]:
        # Prevent from manually setting the primary key.
        kwargs.pop("id", None)
        obj = self.model(**kwargs)
        _, token = self.generate_token(obj)
        obj.save()
        return obj, token

    def get_usable_keys(self) -> models.QuerySet:
        return self.filter(revoked=False)

    def get_from_token(self, token: str) -> "AbstractAPIKey":
        queryset = self.get_usable_keys()

        try:
            entry = queryset.get(token=token)
        except self.model.DoesNotExist:
            raise

        if not entry.is_valid(token):
            raise self.model.DoesNotExist("Key is not valid")
        else:
            return entry

    def is_valid(self, token: str) -> bool:
        try:
            entry = self.get_from_token(token)
        except self.model.DoesNotExist:
            return False

        if entry.has_expired:
            return False

        if not entry.user.is_active:
            return False

        return True


class APIKeyManager(BaseAPIKeyManager):
    pass


class AbstractAPIKey(models.Model):
    """
    Stores a specialized JSON Web Token associated with an individual :model:`users.User`.
    """

    objects = APIKeyManager()

    name = models.CharField(
        max_length=255,
        blank=False,
        default=None,
        help_text=("A name to identify this API key"),
    )
    token = models.TextField(editable=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    expiry_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Expires",
        help_text="Once API key expires, clients cannot use it anymore",
    )
    revoked = models.BooleanField(
        blank=True,
        default=False,
        help_text=("If the API key is revoked, clients cannot use it anymore (this is irreversible)"),
    )
    # Foreign Keys
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        ordering = ("-created",)
        verbose_name = "API key"
        verbose_name_plural = "API keys"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        # Store the initial value of ``revoked`` to detect changes.
        self._initial_revoked = self.revoked

    def _has_expired(self) -> bool:
        if self.expiry_date is None:
            return False
        return self.expiry_date < timezone.now()

    _has_expired.short_description = "Has expired"
    _has_expired.boolean = True
    has_expired = property(_has_expired)

    def is_valid(self, key: str) -> bool:
        payload = jwt_decode_no_verification(key)
        if payload:
            return True
        return False

    def clean(self) -> None:
        self._validate_revoked()

    def save(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._validate_revoked()
        super().save(*args, **kwargs)

    def _validate_revoked(self) -> None:
        if self._initial_revoked and not self.revoked:
            raise ValidationError(
                "The API key has been revoked, which cannot be undone",
                code="revoked",
            )

    def __str__(self) -> str:
        return str(self.name)


class APIKey(AbstractAPIKey):
    """
    Stores a specialized JSON Web Token associated with an individual :model:`users.User`.
    """
