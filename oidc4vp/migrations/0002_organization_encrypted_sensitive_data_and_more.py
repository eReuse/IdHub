# Generated by Django 4.2.5 on 2024-02-23 13:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('oidc4vp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='encrypted_sensitive_data',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='salt',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
    ]
