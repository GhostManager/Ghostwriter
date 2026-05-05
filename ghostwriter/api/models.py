"""This contains all the database models used by the GraphQL application."""

# Standard Libraries
import logging
import secrets
import typing
from datetime import timedelta

# Django Imports
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

# 3rd Party Libraries
import jwt

# Ghostwriter Libraries
from ghostwriter.api.utils import generate_jwt, jwt_decode, jwt_decode_no_verification

User = get_user_model()
logger = logging.getLogger(__name__)
TOKEN_EXPIRY_WARNING_WINDOW = timedelta(days=7)


def _expires_within_warning_window(expiry_date) -> bool:
    if expiry_date is None:
        return False
    now = timezone.now()
    return now <= expiry_date <= now + TOKEN_EXPIRY_WARNING_WINDOW


class ServiceTokenPreset(models.TextChoices):
    OPLOG_RW = "oplog_rw", "Oplog Read/Write"
    PROJECT_READ = "project_read", "Project Read-Only"
    CUSTOM = "custom", "Custom"


class ServiceTokenProjectScope(models.TextChoices):
    SELECTED = "selected", "Selected Projects"
    ALL_ACCESSIBLE = "all_accessible", "All Accessible Projects"


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
    """Stores a specialized JSON Web Token associated with an individual :model:`users.User`."""

    objects = APIKeyManager()

    name = models.CharField(
        max_length=255,
        blank=False,
        default=None,
        help_text="A name to identify this API key",
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
        help_text="If the API key is revoked, clients cannot use it anymore (this is irreversible)",
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

    @property
    def expires_soon(self) -> bool:
        return _expires_within_warning_window(self.expiry_date)

    def is_valid(self, key: str) -> bool:
        try:
            payload = jwt_decode(key)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
            return False
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
    """Stores a specialized JSON Web Token associated with an individual :model:`users.User`."""


class ServicePrincipal(models.Model):
    """A non-human actor that authenticates with one or more service tokens."""

    class ServiceType(models.TextChoices):
        INTEGRATION = "integration", "Integration"
        MYTHIC_SYNC = "mythic_sync", "Mythic Sync"

    name = models.CharField(max_length=255)
    service_type = models.CharField(
        max_length=64, choices=ServiceType.choices, default=ServiceType.INTEGRATION
    )
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="service_principals"
    )

    class Meta:
        ordering = ("name", "id")

    def __str__(self) -> str:
        return self.name


class ServiceTokenManager(models.Manager):
    token_prefix = "gwst"
    last_used_update_interval = timedelta(minutes=5)

    def _build_token(self) -> tuple[str, str, str]:
        prefix = secrets.token_hex(8)
        secret = secrets.token_urlsafe(32)
        return prefix, secret, f"{self.token_prefix}_{prefix}_{secret}"

    def create_token(self, **kwargs: typing.Any) -> tuple["ServiceToken", str]:
        permissions = kwargs.pop("permissions", [])
        kwargs.pop("id", None)
        prefix, secret, token = self._build_token()
        obj = self.model(
            token_prefix=prefix, secret_hash=make_password(secret), **kwargs
        )
        with transaction.atomic():
            obj.save()
            if permissions:
                self._create_permissions(obj, permissions)
        return obj, token

    def _create_permissions(
        self, token: "ServiceToken", permissions: list[dict[str, typing.Any]]
    ) -> None:
        permission_rows = [
            ServiceTokenPermission(
                token=token,
                resource_type=permission["resource_type"],
                resource_id=permission.get("resource_id"),
                action=permission["action"],
                constraints=permission.get("constraints", {}),
            )
            for permission in permissions
        ]
        for permission_row in permission_rows:
            permission_row.full_clean()
        ServiceTokenPermission.objects.bulk_create(permission_rows)

    def get_usable_tokens(self) -> models.QuerySet:
        return self.filter(revoked=False)

    def _split_token(self, token: str) -> tuple[str, str]:
        if not token.startswith(f"{self.token_prefix}_"):
            raise self.model.DoesNotExist("Token prefix is invalid")
        try:
            _, prefix, secret = token.split("_", 2)
        except ValueError as exc:
            raise self.model.DoesNotExist("Token format is invalid") from exc
        return prefix, secret

    def get_from_token(self, token: str) -> "ServiceToken":
        prefix, secret = self._split_token(token)
        try:
            entry = (
                self.get_usable_tokens()
                .select_related(
                    "created_by", "service_principal", "service_principal__created_by"
                )
                .prefetch_related("permissions")
                .get(token_prefix=prefix)
            )
        except self.model.DoesNotExist:
            raise

        if not entry.is_valid(secret):
            raise self.model.DoesNotExist("Token is not valid")
        return entry

    def get_valid_from_token(self, token: str) -> "ServiceToken":
        entry = self.get_from_token(token)
        if entry.has_expired:
            raise self.model.DoesNotExist("Token has expired")

        if not entry.created_by.is_active:
            self.revoke_tokens_for_inactive_user(
                entry.created_by,
                reason="token creator is inactive",
            )
            raise self.model.DoesNotExist("Token creator is inactive")

        if not entry.service_principal.created_by.is_active:
            self.deactivate_service_principal(
                entry.service_principal,
                reason="service principal creator is inactive",
            )
            self.revoke_tokens_for_service_principal(
                entry.service_principal,
                reason="service principal creator is inactive",
            )
            raise self.model.DoesNotExist("Service principal creator is inactive")

        if not entry.service_principal.active:
            raise self.model.DoesNotExist("Service principal is inactive")

        try:
            entry.validate_current_grants()
        except ValidationError as exc:
            self.revoke_token(entry, reason=f"scope validation failed: {exc}")
            raise self.model.DoesNotExist(
                "Service token scope is no longer authorized"
            ) from exc

        return entry

    def revoke_token(self, token: "ServiceToken", *, reason: str | None = None) -> None:
        """Revoke one token without attempting to un-revoke anything."""
        if self.filter(pk=token.pk, revoked=False).update(revoked=True):
            token.revoked = True
            logger.warning(
                "Revoked service token %s (%s)%s",
                token.pk,
                token.name,
                f": {reason}" if reason else "",
            )

    def revoke_tokens_for_inactive_user(
        self, user: User, *, reason: str | None = None
    ) -> None:
        deactivated_principals = ServicePrincipal.objects.filter(
            created_by=user, active=True
        ).update(active=False)
        revoked_tokens = self.filter(created_by=user, revoked=False).update(
            revoked=True
        )
        if deactivated_principals or revoked_tokens:
            logger.warning(
                "Deactivated %s service principal(s) and revoked %s service token(s) for inactive user %s%s",
                deactivated_principals,
                revoked_tokens,
                user.pk,
                f": {reason}" if reason else "",
            )

    def deactivate_service_principal(
        self, service_principal: "ServicePrincipal", *, reason: str | None = None
    ) -> None:
        if service_principal.active:
            ServicePrincipal.objects.filter(
                pk=service_principal.pk, active=True
            ).update(active=False)
            service_principal.active = False
            logger.warning(
                "Deactivated service principal %s (%s)%s",
                service_principal.pk,
                service_principal.name,
                f": {reason}" if reason else "",
            )

    def revoke_tokens_for_service_principal(
        self, service_principal: "ServicePrincipal", *, reason: str | None = None
    ) -> None:
        revoked_tokens = self.filter(
            service_principal=service_principal, revoked=False
        ).update(revoked=True)
        if revoked_tokens:
            logger.warning(
                "Revoked %s service token(s) for service principal %s (%s)%s",
                revoked_tokens,
                service_principal.pk,
                service_principal.name,
                f": {reason}" if reason else "",
            )

    def record_usage(self, token: "ServiceToken", used_at=None) -> bool:
        """Update last_used_at only when it is missing or stale."""
        used_at = used_at or timezone.now()
        stale_before = used_at - self.last_used_update_interval
        updated = (
            self.filter(pk=token.pk)
            .filter(
                models.Q(last_used_at__isnull=True)
                | models.Q(last_used_at__lte=stale_before)
            )
            .update(last_used_at=used_at)
        )
        if updated:
            token.last_used_at = used_at
        return bool(updated)

    def is_valid(self, token: str) -> bool:
        try:
            self.get_valid_from_token(token)
        except self.model.DoesNotExist:
            return False
        return True


class ServiceToken(models.Model):
    """Stores a scoped credential for a :model:`api.ServicePrincipal`."""

    objects = ServiceTokenManager()

    name = models.CharField(max_length=255)
    token_prefix = models.CharField(
        max_length=24, unique=True, editable=False, db_index=True
    )
    secret_hash = models.CharField(max_length=255, editable=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    expiry_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Expires",
        help_text="Once the token expires, clients cannot use it anymore",
    )
    last_used_at = models.DateTimeField(blank=True, null=True)
    revoked = models.BooleanField(
        blank=True,
        default=False,
        help_text="If the service token is revoked, clients cannot use it anymore (this is irreversible)",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="service_tokens"
    )
    service_principal = models.ForeignKey(
        ServicePrincipal, on_delete=models.CASCADE, related_name="tokens"
    )

    class Meta:
        ordering = ("-created",)

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)
        self._initial_revoked = self.revoked

    @property
    def has_expired(self) -> bool:
        if self.expiry_date is None:
            return False
        return self.expiry_date < timezone.now()

    @property
    def expires_soon(self) -> bool:
        return _expires_within_warning_window(self.expiry_date)

    def is_valid(self, secret: str) -> bool:
        return check_password(secret, self.secret_hash)

    def clean(self) -> None:
        self._validate_revoked()

    def save(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._validate_revoked()
        super().save(*args, **kwargs)

    def _validate_revoked(self) -> None:
        if self._initial_revoked and not self.revoked:
            raise ValidationError(
                "The service token has been revoked, which cannot be undone",
                code="revoked",
            )

    @staticmethod
    def build_permissions_for_preset(
        preset: str,
        *,
        oplog_id: int | None = None,
        project_id: int | None = None,
        project_ids: typing.Iterable[int] | None = None,
        all_accessible_projects: bool = False,
    ) -> list[dict[str, typing.Any]]:
        """Return the explicit permission rows required for a supported preset."""
        if preset == ServiceTokenPreset.OPLOG_RW:
            if oplog_id is None:
                raise ValueError("oplog_rw service tokens require an oplog_id")
            return [
                {
                    "resource_type": ServiceTokenPermission.ResourceType.OPLOG,
                    "resource_id": oplog_id,
                    "action": action,
                }
                for action in (
                    ServiceTokenPermission.Action.READ,
                    ServiceTokenPermission.Action.CREATE,
                    ServiceTokenPermission.Action.UPDATE,
                    ServiceTokenPermission.Action.DELETE,
                )
            ]

        if preset == ServiceTokenPreset.PROJECT_READ:
            if all_accessible_projects:
                if project_id is not None or project_ids:
                    raise ValueError(
                        "project_read service tokens require either selected projects or all-accessible scope"
                    )
                return [
                    {
                        "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
                        "resource_id": None,
                        "action": ServiceTokenPermission.Action.READ,
                        "constraints": {
                            ServiceTokenPermission.ConstraintKey.SCOPE: (
                                ServiceTokenPermission.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
                            ),
                        },
                    }
                ]
            if project_ids is None:
                project_ids = [project_id] if project_id is not None else []
            project_scope_ids = sorted(
                {int(project_scope_id) for project_scope_id in project_ids}
            )
            if not project_scope_ids:
                raise ValueError(
                    "project_read service tokens require at least one project_id"
                )
            return [
                {
                    "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
                    "resource_id": project_scope_id,
                    "action": ServiceTokenPermission.Action.READ,
                }
                for project_scope_id in project_scope_ids
            ]

        raise ValueError(f"Unsupported service token preset: {preset}")

    @staticmethod
    def _normalize_permission_values(
        permissions: list[dict[str, typing.Any]],
    ) -> set[tuple[str, int | None, str]]:
        return {
            (
                permission["resource_type"],
                permission.get("resource_id"),
                str(getattr(permission["action"], "value", permission["action"])),
            )
            for permission in permissions
        }

    def _permission_value_set(self) -> set[tuple[str, int | None, str]]:
        return set(
            self.permissions.values_list("resource_type", "resource_id", "action")
        )

    @staticmethod
    def _choice_value(value: typing.Any) -> str:
        return str(getattr(value, "value", value))

    def has_permission(
        self, resource_type: str, action: str, resource_id: int | None
    ) -> bool:
        """Return whether this token is currently authorized for a resource."""
        if resource_id is None:
            return False
        if (
            self._choice_value(resource_type)
            == ServiceTokenPermission.ResourceType.PROJECT
            and self._choice_value(action) == ServiceTokenPermission.Action.READ
        ):
            return resource_id in self.get_current_project_read_ids()
        has_static_permission = self.permissions.filter(
            resource_type=self._choice_value(resource_type),
            action=self._choice_value(action),
            resource_id=resource_id,
        ).exists()
        if has_static_permission:
            return True
        return False

    def _single_resource_id(
        self, resource_type: str, action: str | None = None
    ) -> int | None:
        """Return a single concrete resource scope, or ``None`` if ambiguous."""
        scope_ids = self._resource_ids(resource_type, action)
        if len(scope_ids) != 1:
            return None
        return scope_ids[0]

    def _resource_ids(self, resource_type: str, action: str | None = None) -> list[int]:
        """Return concrete resource IDs for a permission scope."""
        permissions = self.permissions.filter(resource_type=resource_type)
        if action is not None:
            permissions = permissions.filter(action=action)
        scope_ids = set(permissions.values_list("resource_id", flat=True).distinct())
        if None in scope_ids:
            return []
        return sorted(scope_ids)

    def matches_preset(self, preset: str) -> bool:
        """Return whether this token's explicit permissions exactly match a supported preset."""
        try:
            if preset == ServiceTokenPreset.OPLOG_RW:
                oplog_id = self._single_resource_id("oplog")
                if oplog_id is None:
                    return False
                expected = self.build_permissions_for_preset(preset, oplog_id=oplog_id)
            elif preset == ServiceTokenPreset.PROJECT_READ:
                if self.has_all_accessible_project_scope():
                    expected = self.build_permissions_for_preset(
                        preset,
                        all_accessible_projects=True,
                    )
                else:
                    project_ids = self.get_allowed_project_ids()
                    if not project_ids:
                        return False
                    expected = self.build_permissions_for_preset(
                        preset, project_ids=project_ids
                    )
            else:
                return False
        except ValueError:
            return False

        return self._permission_value_set() == self._normalize_permission_values(
            expected
        )

    def get_allowed_oplog_id(self) -> int | None:
        return self._single_resource_id("oplog")

    def get_allowed_project_id(self) -> int | None:
        return self._single_resource_id("project")

    def get_allowed_project_ids(self) -> list[int]:
        return self._resource_ids(
            ServiceTokenPermission.ResourceType.PROJECT,
            ServiceTokenPermission.Action.READ,
        )

    def has_all_accessible_project_scope(self) -> bool:
        return any(
            permission.is_all_accessible_project_scope()
            for permission in self.permissions.filter(
                resource_type=ServiceTokenPermission.ResourceType.PROJECT,
                action=ServiceTokenPermission.Action.READ,
                resource_id__isnull=True,
            )
        )

    def get_current_project_read_ids(self) -> list[int]:
        """Return project IDs this token can read right now."""
        accessible_project_ids = set(self._creator_accessible_project_ids())
        if self.has_all_accessible_project_scope():
            return sorted(accessible_project_ids)
        return sorted(set(self.get_allowed_project_ids()) & accessible_project_ids)

    def get_current_project_read_projects(self):
        """Return project objects this token can read right now."""
        # Ghostwriter Libraries
        from ghostwriter.rolodex.models import Project

        if not self.created_by_id or not self.created_by.is_active:
            return Project.objects.none()

        accessible_project_ids = set(self._creator_accessible_project_ids())
        if self.has_all_accessible_project_scope():
            project_ids = accessible_project_ids
        else:
            project_ids = set(self.get_allowed_project_ids()) & accessible_project_ids

        return (
            Project.objects.filter(id__in=project_ids)
            .select_related("client", "project_type")
            .order_by("complete", "client__name", "codename", "id")
        )

    def get_stale_project_read_ids(self) -> list[int]:
        """Return selected project grants the token creator can no longer access."""
        selected_project_ids = set(self.get_allowed_project_ids())
        if not selected_project_ids:
            return []
        accessible_project_ids = set(self._creator_accessible_project_ids())
        return sorted(selected_project_ids - accessible_project_ids)

    def get_oplog_access_details(self) -> list[dict[str, typing.Any]]:
        """Return oplog access grouped by oplog with user-facing action labels."""
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import Oplog

        action_labels = {
            ServiceTokenPermission.Action.READ.value: "Read oplog and entries",
            ServiceTokenPermission.Action.CREATE.value: "Create entries",
            ServiceTokenPermission.Action.UPDATE.value: "Update entries",
            ServiceTokenPermission.Action.DELETE.value: "Delete entries",
        }
        action_order = list(action_labels)
        actions_by_oplog_id: dict[int, set[str]] = {}
        for permission in self.permissions.filter(
            resource_type=ServiceTokenPermission.ResourceType.OPLOG
        ).exclude(resource_id__isnull=True):
            actions_by_oplog_id.setdefault(permission.resource_id, set()).add(
                permission.action
            )
        if not actions_by_oplog_id:
            return []

        oplogs = (
            Oplog.objects.filter(id__in=actions_by_oplog_id)
            .select_related("project", "project__client")
            .order_by("project__client__name", "project__codename", "name", "id")
        )
        return [
            {
                "oplog": oplog,
                "actions": [
                    action_labels[action]
                    for action in action_order
                    if action in actions_by_oplog_id[oplog.id]
                ],
            }
            for oplog in oplogs
        ]

    def _creator_accessible_project_ids(self) -> list[int]:
        # Ghostwriter Libraries
        from ghostwriter.rolodex.models import Project

        if not self.created_by_id or not self.created_by.is_active:
            return []
        return list(
            Project.for_user(self.created_by).values_list("id", flat=True).distinct()
        )

    def get_token_preset(self) -> str:
        if self.matches_preset(ServiceTokenPreset.OPLOG_RW):
            return ServiceTokenPreset.OPLOG_RW
        if self.matches_preset(ServiceTokenPreset.PROJECT_READ):
            return ServiceTokenPreset.PROJECT_READ

        return ServiceTokenPreset.CUSTOM

    def get_hasura_scope(self) -> dict[str, int | str | None]:
        """
        Return the coarse Hasura scope this token can safely expose.

        Oplog mutation scopes remain scalar and action-specific so read scopes
        do not imply write or delete access. Project-read scopes are enforced
        through the DB-backed service token project access view.
        """
        return {
            "preset": self.get_token_preset(),
            "read_oplog_id": self._single_resource_id(
                ServiceTokenPermission.ResourceType.OPLOG,
                ServiceTokenPermission.Action.READ,
            ),
            "create_oplogentry_oplog_id": self._single_resource_id(
                ServiceTokenPermission.ResourceType.OPLOG,
                ServiceTokenPermission.Action.CREATE,
            ),
            "update_oplogentry_oplog_id": self._single_resource_id(
                ServiceTokenPermission.ResourceType.OPLOG,
                ServiceTokenPermission.Action.UPDATE,
            ),
            "delete_oplogentry_oplog_id": self._single_resource_id(
                ServiceTokenPermission.ResourceType.OPLOG,
                ServiceTokenPermission.Action.DELETE,
            ),
        }

    def get_token_preset_display(self) -> str:
        return ServiceTokenPreset(self.get_token_preset()).label

    def get_scope_display(self) -> str:
        preset = self.get_token_preset()
        oplog_id = self.get_allowed_oplog_id()
        project_id = self.get_allowed_project_id()
        project_ids = self.get_allowed_project_ids()

        if preset == ServiceTokenPreset.OPLOG_RW and oplog_id is not None:
            return f"Oplog #{oplog_id} (R/W)"
        if (
            preset == ServiceTokenPreset.PROJECT_READ
            and self.has_all_accessible_project_scope()
        ):
            return "All Accessible Projects (Read-Only)"
        if preset == ServiceTokenPreset.PROJECT_READ and len(project_ids) == 1:
            return f"Project #{project_id} (Read-Only)"
        if preset == ServiceTokenPreset.PROJECT_READ and project_ids:
            return f"{len(project_ids)} Projects (Read-Only)"
        if oplog_id is not None:
            return f"Oplog #{oplog_id}"
        if project_id is not None:
            return f"Project #{project_id}"
        return "Custom"

    def validate_current_grants(self) -> None:
        """Ensure explicit token grants are still authorized for the creator."""
        self._validate_current_project_grants()
        self._validate_current_oplog_grants()

    def _validate_current_project_grants(self) -> None:
        selected_project_ids = set(self.get_allowed_project_ids())
        if not selected_project_ids:
            return
        accessible_project_ids = set(self._creator_accessible_project_ids())
        stale_project_ids = selected_project_ids - accessible_project_ids
        if not stale_project_ids:
            return
        deleted_count, _ = ServiceTokenPermission.objects.filter(
            token=self,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            action=ServiceTokenPermission.Action.READ,
            resource_id__in=stale_project_ids,
        ).delete()
        self._clear_permission_cache()
        logger.warning(
            "Pruned %s stale project read permission(s) from service token %s (%s): project ids %s",
            deleted_count,
            self.pk,
            self.name,
            sorted(stale_project_ids),
        )
        if not self._has_permission_grants():
            raise ValidationError("Service token project scope is no longer accessible")

    def _has_permission_grants(self) -> bool:
        return self.permissions.exists()

    def _clear_permission_cache(self) -> None:
        getattr(self, "_prefetched_objects_cache", {}).pop("permissions", None)

    def _validate_current_oplog_grants(self) -> None:
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import Oplog

        oplog_permissions = list(
            self.permissions.filter(
                resource_type=ServiceTokenPermission.ResourceType.OPLOG
            )
        )
        if not oplog_permissions:
            return
        oplog_ids = {permission.resource_id for permission in oplog_permissions}
        if None in oplog_ids:
            raise ValidationError("Service token oplog scope is invalid")
        oplogs = {
            oplog.id: oplog
            for oplog in Oplog.objects.filter(id__in=oplog_ids).select_related(
                "project", "project__client"
            )
        }
        if set(oplogs) != oplog_ids:
            raise ValidationError("Service token oplog scope no longer exists")
        for permission in oplog_permissions:
            oplog = oplogs[permission.resource_id]
            if permission.action == ServiceTokenPermission.Action.READ:
                is_authorized = oplog.user_can_view(self.created_by)
            else:
                is_authorized = oplog.user_can_edit(self.created_by)
            if not is_authorized:
                raise ValidationError(
                    "Service token oplog scope is no longer accessible"
                )

    def __str__(self) -> str:
        return self.name


class ServiceTokenPermission(models.Model):
    """Stores an explicit permission grant for a :model:`api.ServiceToken`."""

    class ResourceType(models.TextChoices):
        OPLOG = "oplog", "Oplog"
        PROJECT = "project", "Project"

    class Action(models.TextChoices):
        READ = "read", "Read"
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    class ConstraintKey(models.TextChoices):
        SCOPE = "scope", "Scope"

    class ConstraintScope(models.TextChoices):
        ALL_ACCESSIBLE_PROJECTS = "all_accessible_projects", "All Accessible Projects"

    ALL_ACCESSIBLE_PROJECT_CONSTRAINTS = {
        ConstraintKey.SCOPE.value: ConstraintScope.ALL_ACCESSIBLE_PROJECTS.value,
    }
    ALLOWED_CONSTRAINT_KEYS = {ConstraintKey.SCOPE.value}
    ALLOWED_ACTIONS_BY_RESOURCE = {
        ResourceType.OPLOG: {Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE},
        ResourceType.PROJECT: {Action.READ},
    }

    token = models.ForeignKey(
        ServiceToken, on_delete=models.CASCADE, related_name="permissions"
    )
    resource_type = models.CharField(max_length=64, choices=ResourceType.choices)
    resource_id = models.PositiveIntegerField(blank=True, null=True)
    action = models.CharField(max_length=64, choices=Action.choices)
    constraints = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("resource_type", "resource_id", "action", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["token", "resource_type", "resource_id", "action"],
                condition=models.Q(resource_id__isnull=False),
                name="api_stp_unique_concrete_permission",
            ),
            models.UniqueConstraint(
                fields=["token", "resource_type", "action"],
                condition=models.Q(resource_id__isnull=True),
                name="api_stp_unique_dynamic_permission",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        resource_type="oplog",
                        action__in=["read", "create", "update", "delete"],
                    )
                    | models.Q(resource_type="project", action="read")
                ),
                name="api_stp_allowed_resource_action",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(resource_id__isnull=False, constraints={})
                    | models.Q(
                        resource_type="project",
                        action="read",
                        resource_id__isnull=True,
                        constraints={"scope": "all_accessible_projects"},
                    )
                ),
                name="api_stp_allowed_scope_shape",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        allowed_actions = self.ALLOWED_ACTIONS_BY_RESOURCE.get(self.resource_type)
        if allowed_actions is None:
            raise ValidationError(
                {"resource_type": "Unsupported service token resource type"}
            )
        if self.action not in allowed_actions:
            raise ValidationError(
                {
                    "action": f"{self.resource_type} service token permissions do not support {self.action}"
                }
            )
        if not isinstance(self.constraints, dict):
            raise ValidationError(
                {
                    "constraints": "Service token permission constraints must be a JSON object"
                }
            )
        unknown_constraint_keys = set(self.constraints) - self.ALLOWED_CONSTRAINT_KEYS
        if unknown_constraint_keys:
            raise ValidationError(
                {"constraints": "Unsupported service token permission constraint"}
            )
        if self.is_all_accessible_project_scope():
            if self.constraints != self.ALL_ACCESSIBLE_PROJECT_CONSTRAINTS:
                raise ValidationError(
                    {"constraints": "Invalid all-accessible project scope constraints"}
                )
            if (
                self.resource_type != self.ResourceType.PROJECT
                or self.action != self.Action.READ
            ):
                raise ValidationError(
                    {
                        "constraints": "All-accessible scope is only supported for project read permissions"
                    }
                )
            if self.resource_id is not None:
                raise ValidationError(
                    {
                        "resource_id": "All-accessible project permissions must not target one project"
                    }
                )
            return
        if self.constraints.get(self.ConstraintKey.SCOPE):
            raise ValidationError(
                {"constraints": "Unsupported service token permission scope"}
            )
        if self.constraints:
            raise ValidationError(
                {
                    "constraints": "Concrete service token permissions must not include constraints"
                }
            )
        if self.resource_id is None:
            raise ValidationError(
                {
                    "resource_id": "Service token permissions must target a specific resource"
                }
            )

    def is_all_accessible_project_scope(self) -> bool:
        return (
            self.constraints.get(self.ConstraintKey.SCOPE)
            == self.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
        )

    def save(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        resource_id = self.resource_id if self.resource_id is not None else "*"
        return f"{self.resource_type}:{resource_id}:{self.action}"
