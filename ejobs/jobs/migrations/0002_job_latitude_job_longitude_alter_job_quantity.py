# Generated by Django 5.1 on 2024-09-07 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='latitude',
            field=models.FloatField(default=10.5),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='longitude',
            field=models.FloatField(default=10.5),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='job',
            name='quantity',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
