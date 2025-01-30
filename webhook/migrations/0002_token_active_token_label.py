# Generated by Django 4.2.5 on 2025-01-27 09:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('webhook', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='token',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
        migrations.AddField(
            model_name='token',
            name='label',
            field=models.CharField(default='', max_length=250, verbose_name='Label'),
        ),
    ]
