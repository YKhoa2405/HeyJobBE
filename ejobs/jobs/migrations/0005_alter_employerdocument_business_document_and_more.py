# Generated by Django 5.1 on 2024-08-29 06:09

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_job_quantity_jobapplication_email_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employerdocument',
            name='business_document',
            field=models.FileField(blank=True, null=True, upload_to='documents/'),
        ),
        migrations.AlterField(
            model_name='employerdocument',
            name='tax_document',
            field=models.FileField(blank=True, null=True, upload_to='documents/'),
        ),
        migrations.AlterField(
            model_name='employerimage',
            name='url',
            field=models.FileField(default=django.utils.timezone.now, upload_to='documents/'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='jobapplication',
            name='cv',
            field=models.FileField(upload_to='documents/'),
        ),
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.FileField(upload_to='documents/'),
        ),
    ]
