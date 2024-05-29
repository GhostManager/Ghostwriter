from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0012_auto_20240220_1810"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="enable_client_list_all",
            field=models.BooleanField(
                default=False,
                help_text="Allow the user to view all clients (only applies to accounts with the User role)",
                verbose_name="Allow Listing All Clients",
            ),
        ),
    ]
