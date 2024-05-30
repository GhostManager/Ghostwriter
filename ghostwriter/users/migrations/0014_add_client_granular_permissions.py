from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0013_add_client_list_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="enable_client_create",
            field=models.BooleanField(
                default=False,
                help_text="Allow the user to create new clients in the library (only applies to account with the User role)",
                verbose_name="Allow Client Creation",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="enable_client_delete",
            field=models.BooleanField(
                default=False,
                help_text="Allow the user to delete clients in the library (only applies to accounts with the User role)",
                verbose_name="Allow Client Deletion",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="enable_client_edit",
            field=models.BooleanField(
                default=False,
                help_text="Allow the user to edit clients in the library (only applies to accounts with the User role)",
                verbose_name="Allow Client Editing",
            ),
        ),
    ]
