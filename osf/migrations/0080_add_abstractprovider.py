# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-15 19:48
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
        ('osf', '0079_merge_20180207_1545'),
    ]

    operations = [
        migrations.CreateModel(
            name='AbstractProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('reviews_workflow', models.CharField(blank=True, choices=[(None, 'None'), ('pre-moderation', 'Pre-Moderation'), ('post-moderation', 'Post-Moderation')], max_length=15, null=True)),
                ('reviews_comments_private', models.NullBooleanField()),
                ('reviews_comments_anonymous', models.NullBooleanField()),
                ('type', models.CharField(choices=[('osf.preprintprovider', 'preprint provider')], db_index=True, max_length=255)),
                ('name', models.CharField(max_length=128)),
                ('advisory_board', models.TextField(blank=True, default='')),
                ('description', models.TextField(blank=True, default='')),
                ('domain', models.URLField(blank=True, default='')),
                ('domain_redirect_enabled', models.BooleanField(default=False)),
                ('external_url', models.URLField(blank=True, null=True)),
                ('email_contact', models.CharField(blank=True, max_length=200, null=True)),
                ('email_support', models.CharField(blank=True, max_length=200, null=True)),
                ('social_twitter', models.CharField(blank=True, max_length=200, null=True)),
                ('social_facebook', models.CharField(blank=True, max_length=200, null=True)),
                ('social_instagram', models.CharField(blank=True, max_length=200, null=True)),
                ('footer_links', models.TextField(blank=True, default='')),
                ('facebook_app_id', models.BigIntegerField(blank=True, null=True)),
                ('example', models.CharField(blank=True, max_length=20, null=True)),
                ('allow_submissions', models.BooleanField(default=True)),
                ('share_publish_type', models.CharField(choices=[('Preprint', 'Preprint'), ('Thesis', 'Thesis')], default='Preprint', help_text='This SHARE type will be used when pushing publications to SHARE', max_length=32, null=True)),
                ('share_source', models.CharField(blank=True, max_length=200, null=True)),
                ('share_title', models.TextField(blank=True, default='', null=True)),
                ('additional_providers', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, null=True, size=None)),
                ('access_token', osf.utils.fields.EncryptedTextField(blank=True, null=True)),
                ('preprint_word', models.CharField(choices=[('preprint', 'Preprint'), ('paper', 'Paper'), ('thesis', 'Thesis'), ('none', 'None')], default='preprint', max_length=10, null=True)),
                ('subjects_acceptable', osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder, null=True)),
                ('default_license', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='default_license', to='osf.NodeLicense')),
                ('licenses_acceptable', models.ManyToManyField(blank=True, related_name='licenses_acceptable', to='osf.NodeLicense')),
            ],
            options={
                'abstract': False,
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
        migrations.RunSQL(
            [
                """
                INSERT INTO osf_abstractprovider (id, created, modified, _id,
                        reviews_workflow, reviews_comments_private, reviews_comments_anonymous, name, advisory_board, description,
                        domain, domain_redirect_enabled, external_url, email_contact, email_support, social_twitter, social_facebook, social_instagram,
                        footer_links, facebook_app_id, example, allow_submissions, share_publish_type, share_source, share_title, additional_providers,
                        access_token, preprint_word, subjects_acceptable, default_license_id, type)
                    SELECT id, created, modified, _id,
                        reviews_workflow, reviews_comments_private, reviews_comments_anonymous, name, advisory_board, description,
                        domain, domain_redirect_enabled, external_url, email_contact, email_support, social_twitter, social_facebook, social_instagram,
                        footer_links, facebook_app_id, example, allow_submissions, share_publish_type, share_source, share_title, additional_providers,
                        access_token, preprint_word, subjects_acceptable, default_license_id, 'osf.preprintprovider' as type
                    FROM osf_preprintprovider;
                INSERT INTO osf_abstractprovider_licenses_acceptable (id, abstractprovider_id, nodelicense_id)
                    SELECT id, preprintprovider_id, nodelicense_id
                    FROM osf_preprintprovider_licenses_acceptable
                """
            ], [
                """
                INSERT INTO osf_preprintprovider_licenses_acceptable (id, preprintprovider_id, nodelicense_id)
                    SELECT id, abstractprovider_id, nodelicense_id
                    FROM osf_abstractprovider_licenses_acceptable
                """
            ]
        ),
        migrations.AlterField(
            model_name='subject',
            name='provider',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='subjects', to='osf.AbstractProvider'),
        ),
        migrations.RunSQL(
            migrations.RunSQL.noop,
            [
                """
                INSERT INTO osf_preprintprovider (id, created, modified, _id,
                        reviews_workflow, reviews_comments_private, reviews_comments_anonymous, name, advisory_board, description,
                        domain, domain_redirect_enabled, external_url, email_contact, email_support, social_twitter, social_facebook, social_instagram,
                        footer_links, facebook_app_id, example, allow_submissions, share_publish_type, share_source, share_title, additional_providers,
                        access_token, preprint_word, subjects_acceptable, default_license_id)
                    SELECT id, created, modified, _id,
                        reviews_workflow, reviews_comments_private, reviews_comments_anonymous, name, advisory_board, description,
                        domain, domain_redirect_enabled, external_url, email_contact, email_support, social_twitter, social_facebook, social_instagram,
                        footer_links, facebook_app_id, example, allow_submissions, share_publish_type, share_source, share_title, additional_providers,
                        access_token, preprint_word, subjects_acceptable, default_license_id
                    FROM osf_abstractprovider
                """
            ]
        ),
        migrations.RemoveField(
            model_name='preprintprovider',
            name='default_license',
        ),
        migrations.RemoveField(
            model_name='preprintprovider',
            name='licenses_acceptable',
        ),
        migrations.DeleteModel(
            name='PreprintProvider',
        ),
        migrations.CreateModel(
            name='PreprintProvider',
            fields=[
            ],
            bases=('osf.abstractprovider',),
        ),
    ]
