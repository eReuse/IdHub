# Generated by Django 4.2.5 on 2023-11-09 13:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('idhub', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
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
                ('message', models.CharField(max_length=350)),
                (
                    'type',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, 'EV_USR_REGISTERED'),
                            (2, 'EV_USR_WELCOME'),
                            (3, 'EV_DATA_UPDATE_REQUESTED_BY_USER'),
                            (4, 'EV_DATA_UPDATE_REQUESTED'),
                            (5, 'EV_USR_UPDATED_BY_ADMIN'),
                            (6, 'EV_USR_UPDATED'),
                            (7, 'EV_USR_DELETED_BY_ADMIN'),
                            (8, 'EV_DID_CREATED_BY_USER'),
                            (9, 'EV_DID_CREATED'),
                            (10, 'EV_DID_DELETED'),
                            (11, 'EV_CREDENTIAL_DELETED_BY_ADMIN'),
                            (12, 'EV_CREDENTIAL_DELETED'),
                            (13, 'EV_CREDENTIAL_ISSUED_FOR_USER'),
                            (14, 'EV_CREDENTIAL_ISSUED'),
                            (15, 'EV_CREDENTIAL_PRESENTED_BY_USER'),
                            (16, 'EV_CREDENTIAL_PRESENTED'),
                            (17, 'EV_CREDENTIAL_ENABLED'),
                            (18, 'EV_CREDENTIAL_CAN_BE_REQUESTED'),
                            (19, 'EV_CREDENTIAL_REVOKED_BY_ADMIN'),
                            (20, 'EV_CREDENTIAL_REVOKED'),
                            (21, 'EV_ROLE_CREATED_BY_ADMIN'),
                            (22, 'EV_ROLE_MODIFIED_BY_ADMIN'),
                            (23, 'EV_ROLE_DELETED_BY_ADMIN'),
                            (24, 'EV_SERVICE_CREATED_BY_ADMIN'),
                            (25, 'EV_SERVICE_MODIFIED_BY_ADMIN'),
                            (26, 'EV_SERVICE_DELETED_BY_ADMIN'),
                            (27, 'EV_ORG_DID_CREATED_BY_ADMIN'),
                            (28, 'EV_ORG_DID_DELETED_BY_ADMIN'),
                            (29, 'EV_USR_DEACTIVATED_BY_ADMIN'),
                            (30, 'EV_USR_ACTIVATED_BY_ADMIN'),
                        ]
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='events',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
