# Generated by Django 3.2.15 on 2022-12-08 20:21

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.models.validators


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0004_django3_upgrade'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomMetadataProperty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('property_uri', models.URLField()),
                ('value_as_text', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.CreateModel(
            name='GuidMetadataRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('language', models.TextField(blank=True)),
                ('resource_type_general', models.TextField(blank=True)),
                ('funding_info', models.JSONField(default=list, validators=[osf.models.validators.JsonschemaValidator({'items': {'additionalProperties': False, 'properties': {'award_number': {'type': 'string'}, 'award_title': {'type': 'string'}, 'award_uri': {'type': 'string'}, 'funder_identifier': {'type': 'string'}, 'funder_identifier_type': {'type': 'string'}, 'funder_name': {'type': 'string'}}, 'required': [], 'type': 'object'}, 'type': 'array'})])),
                ('guid', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='metadata_record', to='osf.guid')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.DeleteModel(
            name='FileMetadataRecord',
        ),
        migrations.AddField(
            model_name='custommetadataproperty',
            name='metadata_record',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_property_set', to='osf.guidmetadatarecord'),
        ),
    ]
