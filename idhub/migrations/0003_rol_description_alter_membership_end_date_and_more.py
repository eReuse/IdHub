# Generated by Django 4.2.5 on 2023-11-14 09:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('idhub', '0002_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='rol',
            name='description',
            field=models.CharField(
                max_length=250, null=True, verbose_name='Description'
            ),
        ),
        migrations.AlterField(
            model_name='membership',
            name='end_date',
            field=models.DateField(
                blank=True,
                help_text='What date will the membership end?',
                null=True,
                verbose_name='End date',
            ),
        ),
        migrations.AlterField(
            model_name='membership',
            name='type',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Beneficiary'), (2, 'Employee'), (3, 'Member')],
                verbose_name='Type of membership',
            ),
        ),
        migrations.AlterField(
            model_name='rol',
            name='name',
            field=models.CharField(max_length=250, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='service',
            name='description',
            field=models.CharField(max_length=250, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='service',
            name='domain',
            field=models.CharField(max_length=250, verbose_name='Domain'),
        ),
    ]
