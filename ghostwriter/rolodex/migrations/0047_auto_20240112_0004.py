# Generated by Django 3.2.19 on 2024-01-12 00:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rolodex', '0046_auto_20240111_2238'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='clientcontact',
            unique_together={('name', 'client')},
        ),
        migrations.AlterUniqueTogether(
            name='projectcontact',
            unique_together={('name', 'project')},
        ),
    ]
