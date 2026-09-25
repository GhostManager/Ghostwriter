from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_enable_template_management"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="report_email",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="Optional email address to display for this user in project and report team lists",
                max_length=254,
                verbose_name="Report Email",
            ),
        ),
    ]
