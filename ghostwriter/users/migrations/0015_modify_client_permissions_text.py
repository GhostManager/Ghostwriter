from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_add_client_granular_permissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="enable_client_create",
            field=models.BooleanField(
                help_text="Allow the user to create new clients in the library and create projects for any client (only applies to account with the User role)",
                verbose_name="Allow Client  and Project Creation",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="enable_client_delete",
            field=models.BooleanField(
                help_text="Allow the user to delete clients in the library and delete projects for any client (only applies to accounts with the User role)",
                verbose_name="Allow Client and Project Deletion",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="enable_client_edit",
            field=models.BooleanField(
                help_text="Allow the user to edit clients in the library and edit projects for any client (only applies to accounts with the User role)",
                verbose_name="Allow Client and Project Editing",
            ),
        ),
    ]
