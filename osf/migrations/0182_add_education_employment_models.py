# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-01-29 16:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base

from django.conf import settings
from osf.management.commands.migrate_education_employment import populate_new_models, put_jobs_and_schools_back

if settings.TEST_MIGRATION:
    run_migration = lambda *args, **kwargs: None
    reverse_migration = lambda *args, **kwargs: None
else:
    run_migration = populate_new_models
    reverse_migration = put_jobs_and_schools_back

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0181_osfuser_contacted_deactivation'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserEducation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('institution', models.CharField(max_length=650)),
                ('department', models.CharField(blank=True, max_length=650, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('ongoing', models.BooleanField(default=False)),
                ('degree', models.CharField(blank=True, max_length=650, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='education', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserEmployment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('institution', models.CharField(max_length=650)),
                ('department', models.CharField(blank=True, max_length=650, null=True)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('ongoing', models.BooleanField(default=False)),
                ('title', models.CharField(blank=True, max_length=650, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employment', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterOrderWithRespectTo(
            name='useremployment',
            order_with_respect_to='user',
        ),
        migrations.AlterOrderWithRespectTo(
            name='usereducation',
            order_with_respect_to='user',
        ),
        migrations.RunPython(run_migration, reverse_migration),
    ]
