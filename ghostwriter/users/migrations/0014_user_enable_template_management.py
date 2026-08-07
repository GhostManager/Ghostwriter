from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_remove_user_require_2fa_user_require_mfa"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="enable_template_management",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Allow the user to manage global and protected report templates "
                    "without granting manager access to clients and projects"
                ),
                verbose_name="Allow Report Template Management",
            ),
        ),
    ]
