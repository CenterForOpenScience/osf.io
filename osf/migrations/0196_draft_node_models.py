# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-11-15 15:34
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import osf.models.validators
import osf.utils.datetime_aware_jsonfield
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('osf', '0195_update_schemas'),
    ]

    operations = [
        migrations.CreateModel(
            name='DraftRegistrationContributor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visible', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DraftRegistrationGroupObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DraftRegistrationUserObjectPermission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DraftNode',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('osf.abstractnode',),
        ),
        migrations.AlterModelOptions(
            name='draftregistration',
            options={'permissions': (('read_draft_registration', 'Can read the draft registration'), ('write_draft_registration', 'Can edit the draft registration'), ('admin_draft_registration', 'Can manage the draft registration'))},
        ),
        migrations.AlterModelOptions(
            name='draftregistrationlog',
            options={'get_latest_by': 'created', 'ordering': ['-created']},
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='affiliated_institutions',
            field=models.ManyToManyField(related_name='draft_registrations', to='osf.Institution'),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='category',
            field=models.CharField(blank=True, choices=[(b'', b'Uncategorized'), (b'communication', b'Communication'), (b'hypothesis', b'Hypothesis'), (b'data', b'Data'), (b'instrumentation', b'Instrumentation'), (b'methods and measures', b'Methods and Measures'), (b'analysis', b'Analysis'), (b'project', b'Project'), (b'other', b'Other'), (b'procedure', b'Procedure'), (b'software', b'Software')], default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='description',
            field=models.TextField(blank=True, default=b''),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='last_logged',
            field=osf.utils.fields.NonNaiveDateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, null=True),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='node_license',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='draft_registrations', to='osf.NodeLicenseRecord'),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='subjects',
            field=models.ManyToManyField(blank=True, related_name='draftregistrations', to='osf.Subject'),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='tags',
            field=models.ManyToManyField(related_name='draftregistration_tagged', to='osf.Tag'),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='title',
            field=models.TextField(blank=True, default=b'', validators=[osf.models.validators.validate_title]),
        ),
        migrations.AddField(
            model_name='draftregistrationlog',
            name='params',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='type',
            field=models.CharField(choices=[('osf.node', 'node'), ('osf.draftnode', 'draft node'), ('osf.registration', 'registration'), ('osf.quickfilesnode', 'quick files node')], db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='draftregistration',
            name='branched_from',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='registered_draft', to='osf.AbstractNode'),
        ),
        migrations.AlterField(
            model_name='draftregistrationlog',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='draftregistrationuserobjectpermission',
            name='content_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf.DraftRegistration'),
        ),
        migrations.AddField(
            model_name='draftregistrationuserobjectpermission',
            name='permission',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Permission'),
        ),
        migrations.AddField(
            model_name='draftregistrationuserobjectpermission',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='draftregistrationgroupobjectpermission',
            name='content_object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf.DraftRegistration'),
        ),
        migrations.AddField(
            model_name='draftregistrationgroupobjectpermission',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group'),
        ),
        migrations.AddField(
            model_name='draftregistrationgroupobjectpermission',
            name='permission',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Permission'),
        ),
        migrations.AddField(
            model_name='draftregistrationcontributor',
            name='draft_registration',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf.DraftRegistration'),
        ),
        migrations.AddField(
            model_name='draftregistrationcontributor',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='_contributors',
            field=models.ManyToManyField(related_name='draft_registrations', through='osf.DraftRegistrationContributor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='draftregistrationuserobjectpermission',
            unique_together=set([('user', 'permission', 'content_object')]),
        ),
        migrations.AlterUniqueTogether(
            name='draftregistrationgroupobjectpermission',
            unique_together=set([('group', 'permission', 'content_object')]),
        ),
        migrations.AlterUniqueTogether(
            name='draftregistrationcontributor',
            unique_together=set([('user', 'draft_registration')]),
        ),
        migrations.AlterOrderWithRespectTo(
            name='draftregistrationcontributor',
            order_with_respect_to='draft_registration',
        ),
    ]
