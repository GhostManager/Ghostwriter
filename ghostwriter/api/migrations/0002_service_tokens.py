# Django Imports
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServicePrincipal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("integration", "Integration"),
                            ("mythic_sync", "Mythic Sync"),
                        ],
                        default="integration",
                        max_length=64,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_principals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("name", "id"),
            },
        ),
        migrations.CreateModel(
            name="ServiceToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "token_prefix",
                    models.CharField(
                        db_index=True, editable=False, max_length=24, unique=True
                    ),
                ),
                ("secret_hash", models.CharField(editable=False, max_length=255)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "expiry_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Once the token expires, clients cannot use it anymore",
                        null=True,
                        verbose_name="Expires",
                    ),
                ),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "revoked",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="If the service token is revoked, clients cannot use it anymore (this is irreversible)",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "service_principal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tokens",
                        to="api.serviceprincipal",
                    ),
                ),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
        migrations.CreateModel(
            name="ServiceTokenPermission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        choices=[("oplog", "Oplog"), ("project", "Project")],
                        max_length=64,
                    ),
                ),
                ("resource_id", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("read", "Read"),
                            ("create", "Create"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                        ],
                        max_length=64,
                    ),
                ),
                ("constraints", models.JSONField(blank=True, default=dict)),
                (
                    "token",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permissions",
                        to="api.servicetoken",
                    ),
                ),
            ],
            options={
                "ordering": ("resource_type", "resource_id", "action", "id"),
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("resource_id__isnull", False)),
                        fields=("token", "resource_type", "resource_id", "action"),
                        name="api_stp_unique_concrete_permission",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("resource_id__isnull", True)),
                        fields=("token", "resource_type", "action"),
                        name="api_stp_unique_dynamic_permission",
                    ),
                    models.CheckConstraint(
                        check=(
                            models.Q(
                                ("action__in", ["read", "create", "update", "delete"]),
                                ("resource_type", "oplog"),
                            )
                            | models.Q(("action", "read"), ("resource_type", "project"))
                        ),
                        name="api_stp_allowed_resource_action",
                    ),
                    models.CheckConstraint(
                        check=(
                            models.Q(
                                ("constraints", {}), ("resource_id__isnull", False)
                            )
                            | models.Q(
                                ("action", "read"),
                                ("constraints", {"scope": "all_accessible_projects"}),
                                ("resource_id__isnull", True),
                                ("resource_type", "project"),
                            )
                        ),
                        name="api_stp_allowed_scope_shape",
                    ),
                ],
            },
        ),
    ]
