# Generated by Django 4.2.5 on 2024-01-22 15:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import oidc4vp.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Authorization',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'code',
                    models.CharField(default=oidc4vp.models.set_code, max_length=24),
                ),
                ('code_used', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now=True)),
                ('presentation_definition', models.CharField(max_length=250)),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('name', models.CharField(max_length=250)),
                (
                    'client_id',
                    models.CharField(
                        default=oidc4vp.models.set_client_id, max_length=24, unique=True
                    ),
                ),
                (
                    'client_secret',
                    models.CharField(
                        default=oidc4vp.models.set_client_secret, max_length=48
                    ),
                ),
                ('my_client_id', models.CharField(max_length=24)),
                ('my_client_secret', models.CharField(max_length=48)),
                (
                    'response_uri',
                    models.URLField(
                        help_text='Url where to send the verificable presentation',
                        max_length=250,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='OAuth2VPToken',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('created', models.DateTimeField(auto_now=True)),
                ('result_verify', models.CharField(max_length=255)),
                ('vp_token', models.TextField()),
                (
                    'authorization',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='vp_tokens',
                        to='oidc4vp.authorization',
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='vp_tokens',
                        to='oidc4vp.organization',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='vp_tokens',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='authorization',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='authorizations',
                to='oidc4vp.organization',
            ),
        ),
        migrations.AddField(
            model_name='authorization',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
