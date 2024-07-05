# Generated by Django 3.2.17 on 2023-11-01 15:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields

import addons.base.models
import osf.models.base
import osf.utils.datetime_aware_jsonfield
import osf.utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('osf', '0016_auto_20230828_1810'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted', osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True)),
                ('oauth_grants', osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder)),
                ('owner', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_boa_user_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.CreateModel(
            name='NodeSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted', osf.utils.fields.NonNaiveDateTimeField(blank=True, null=True)),
                ('folder_id', models.TextField(blank=True, null=True)),
                ('external_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_boa_node_settings', to='osf.externalaccount')),
                ('owner', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='addons_boa_node_settings', to='osf.abstractnode')),
                ('user_settings', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_boa.usersettings')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin, addons.base.models.BaseStorageAddon),
        ),
    ]
