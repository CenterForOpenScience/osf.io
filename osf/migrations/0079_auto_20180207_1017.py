# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-07 16:17
from __future__ import unicode_literals

import dirtyfields.dirtyfields
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.utils.datetime_aware_jsonfield
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0078_merge_20180206_1148'),
    ]

    operations = [
        migrations.CreateModel(
            name='AbstractProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('reviews_workflow', models.CharField(blank=True, choices=[(None, 'None'), ('post-moderation', 'Post-Moderation'), ('pre-moderation', 'Pre-Moderation')], max_length=15, null=True)),
                ('reviews_comments_private', models.NullBooleanField()),
                ('reviews_comments_anonymous', models.NullBooleanField()),
                ('type', models.CharField(choices=[('osf.preprintprovider', 'preprint provider')], db_index=True, max_length=255)),
                ('name', models.CharField(max_length=128)),
                ('advisory_board', models.TextField(blank=True, default=b'')),
                ('description', models.TextField(blank=True, default=b'')),
                ('domain', models.URLField(blank=True, default=b'')),
                ('domain_redirect_enabled', models.BooleanField(default=False)),
                ('external_url', models.URLField(blank=True, null=True)),
                ('email_contact', models.CharField(blank=True, max_length=200, null=True)),
                ('email_support', models.CharField(blank=True, max_length=200, null=True)),
                ('social_twitter', models.CharField(blank=True, max_length=200, null=True)),
                ('social_facebook', models.CharField(blank=True, max_length=200, null=True)),
                ('social_instagram', models.CharField(blank=True, max_length=200, null=True)),
                ('footer_links', models.TextField(blank=True, default=b'')),
                ('facebook_app_id', models.BigIntegerField(blank=True, null=True)),
                ('example', models.CharField(blank=True, max_length=20, null=True)),
                ('allow_submissions', models.BooleanField(default=True)),
                ('share_publish_type', models.CharField(choices=[(b'Preprint', b'Preprint'), (b'Thesis', b'Thesis')], default=b'Preprint', help_text=b'This SHARE type will be used when pushing publications to SHARE', max_length=32, null=True)),
                ('share_source', models.CharField(blank=True, max_length=200, null=True)),
                ('share_title', models.TextField(blank=True, default=b'', null=True)),
                ('additional_providers', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, null=True, size=None)),
                ('access_token', osf.utils.fields.EncryptedTextField(blank=True, null=True)),
                ('preprint_word', models.CharField(choices=[(b'preprint', b'Preprint'), (b'paper', b'Paper'), (b'thesis', b'Thesis'), (b'none', b'None')], default=b'preprint', max_length=10, null=True)),
                ('subjects_acceptable', osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder, null=True)),
                ('default_license', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='default_license', to='osf.NodeLicense')),
                ('licenses_acceptable', models.ManyToManyField(blank=True, related_name='licenses_acceptable', to='osf.NodeLicense')),
            ],
            options={
                'abstract': False,
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
        migrations.RemoveField(
            model_name='preprintprovider',
            name='default_license',
        ),
        migrations.RemoveField(
            model_name='preprintprovider',
            name='licenses_acceptable',
        ),
        migrations.AlterField(
            model_name='subject',
            name='provider',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subjects', to='osf.AbstractProvider'),
        ),
        migrations.DeleteModel(
            name='PreprintProvider',
        ),
        migrations.CreateModel(
            name='PreprintProvider',
            fields=[
            ],
            options={
                'indexes': [],
                'proxy': True,
                'permissions': (('view_submissions', 'Can view all submissions to this provider'), ('add_moderator', 'Can add other users as moderators for this provider'), ('view_actions', 'Can view actions on submissions to this provider'), ('add_reviewer', 'Can add other users as reviewers for this provider'), ('review_assigned_submissions', 'Can submit reviews for submissions to this provider which have been assigned to this user'), ('assign_reviewer', 'Can assign reviewers to review specific submissions to this provider'), ('set_up_moderation', 'Can set up moderation for this provider'), ('view_assigned_submissions', 'Can view submissions to this provider which have been assigned to this user'), ('edit_reviews_settings', 'Can edit reviews settings for this provider'), ('accept_submissions', 'Can accept submissions to this provider'), ('reject_submissions', 'Can reject submissions to this provider'), ('edit_review_comments', 'Can edit comments on actions for this provider'), ('view_preprintprovider', 'Can view preprint provider details')),
            },
            bases=('osf.abstractprovider',),
        ),
    ]
