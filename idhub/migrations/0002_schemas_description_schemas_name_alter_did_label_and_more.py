# Generated by Django 4.2.5 on 2024-01-03 18:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('idhub', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='schemas',
            name='description',
            field=models.CharField(max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='schemas',
            name='name',
            field=models.CharField(max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name='did',
            name='label',
            field=models.CharField(max_length=50, verbose_name='Label'),
        ),
        migrations.AlterField(
            model_name='event',
            name='created',
            field=models.DateTimeField(auto_now=True, verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='event',
            name='message',
            field=models.CharField(max_length=350, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='event',
            name='type',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, 'User registered'),
                    (2, 'User welcomed'),
                    (3, 'Data update requested by user'),
                    (4, 'Data update requested. Pending approval by administrator'),
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
                ],
                verbose_name='Event',
            ),
        ),
        migrations.AlterField(
            model_name='userrol',
            name='service',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='users',
                to='idhub.service',
                verbose_name='Service',
            ),
        ),
    ]
