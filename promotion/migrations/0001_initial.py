# Generated by Django 4.2.5 on 2024-01-11 10:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('oidc4vp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Promotion',
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
                    'discount',
                    models.PositiveSmallIntegerField(
                        choices=[(1, 'Financial vulnerability')]
                    ),
                ),
                (
                    'authorize',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='promotions',
                        to='oidc4vp.authorization',
                    ),
                ),
            ],
        ),
    ]
