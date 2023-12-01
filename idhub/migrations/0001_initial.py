# Generated by Django 4.2.5 on 2023-12-01 18:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DID',
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
                ('created_at', models.DateTimeField(auto_now=True)),
                ('label', models.CharField(max_length=50)),
                ('did', models.CharField(max_length=250)),
                ('key_material', models.CharField(max_length=250)),
                (
                    'user',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='dids',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='File_datas',
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
                ('file_name', models.CharField(max_length=250)),
                ('success', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Rol',
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
                ('name', models.CharField(max_length=250, verbose_name='name')),
                (
                    'description',
                    models.CharField(
                        max_length=250, null=True, verbose_name='Description'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Schemas',
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
                ('type', models.CharField(max_length=250)),
                ('file_schema', models.CharField(max_length=250)),
                ('data', models.TextField()),
                ('created_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Service',
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
                ('domain', models.CharField(max_length=250, verbose_name='Domain')),
                (
                    'description',
                    models.CharField(max_length=250, verbose_name='Description'),
                ),
                ('rol', models.ManyToManyField(to='idhub.rol')),
            ],
        ),
        migrations.CreateModel(
            name='VCTemplate',
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
                ('wkit_template_id', models.CharField(max_length=250)),
                ('data', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='VerificableCredential',
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
                ('id_string', models.CharField(max_length=250)),
                ('verified', models.BooleanField()),
                ('created_on', models.DateTimeField(auto_now=True)),
                ('issued_on', models.DateTimeField(null=True)),
                ('data', models.TextField()),
                ('csv_data', models.TextField()),
                (
                    'status',
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, 'Enabled'),
                            (2, 'Issued'),
                            (3, 'Revoked'),
                            (4, 'Expired'),
                        ],
                        default=1,
                    ),
                ),
                (
                    'issuer_did',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='vcredentials',
                        to='idhub.did',
                    ),
                ),
                (
                    'schema',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='vcredentials',
                        to='idhub.schemas',
                    ),
                ),
                (
                    'subject_did',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='subject_credentials',
                        to='idhub.did',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='vcredentials',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
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
                    'type',
                    models.PositiveSmallIntegerField(
                        choices=[(1, 'Beneficiary'), (2, 'Employee'), (3, 'Member')],
                        verbose_name='Type of membership',
                    ),
                ),
                (
                    'start_date',
                    models.DateField(
                        blank=True,
                        help_text='What date did the membership start?',
                        null=True,
                        verbose_name='Start date',
                    ),
                ),
                (
                    'end_date',
                    models.DateField(
                        blank=True,
                        help_text='What date will the membership end?',
                        null=True,
                        verbose_name='End date',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='memberships',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
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
                            (1, 'User registered'),
                            (2, 'User welcomed'),
                            (3, 'Data update requested by user'),
                            (
                                4,
                                'Data update requested. Pending approval by administrator',
                            ),
                            (5, "User's data updated by admin"),
                            (6, 'Your data updated by admin'),
                            (7, 'User deactivated by admin'),
                            (8, 'DID created by user'),
                            (9, 'DID created'),
                            (10, 'DID deleted'),
                            (11, 'Credential deleted by user'),
                            (12, 'Credential deleted'),
                            (13, 'Credential issued for user'),
                            (14, 'Credential issued'),
                            (15, 'Credential presented by user'),
                            (16, 'Credential presented'),
                            (17, 'Credential enabled'),
                            (18, 'Credential available'),
                            (19, 'Credential revoked by admin'),
                            (20, 'Credential revoked'),
                            (21, 'Role created by admin'),
                            (22, 'Role modified by admin'),
                            (23, 'Role deleted by admin'),
                            (24, 'Service created by admin'),
                            (25, 'Service modified by admin'),
                            (26, 'Service deleted by admin'),
                            (27, 'Organisational DID created by admin'),
                            (28, 'Organisational DID deleted by admin'),
                            (29, 'User deactivated'),
                            (30, 'User activated'),
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
        migrations.CreateModel(
            name='UserRol',
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
                    'service',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='users',
                        to='idhub.service',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='roles',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'unique_together': {('user', 'service')},
            },
        ),
    ]
