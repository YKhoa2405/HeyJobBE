# Generated by Django 5.1 on 2024-08-30 07:33

import s3direct.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0009_alter_jobapplication_cv'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobapplication',
            name='cv',
            field=s3direct.fields.S3DirectField(),
        ),
    ]
