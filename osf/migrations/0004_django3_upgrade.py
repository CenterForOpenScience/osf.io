# Generated by Django 3.2.15 on 2022-10-21 00:40

import django.contrib.postgres.fields
from django.db import migrations, models
import osf.utils.datetime_aware_jsonfield


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('osf', '0003_aggregated_runsql_calls'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='brand',
            options={'permissions': (('modify_brand', 'Can modify brands'),)},
        ),
        migrations.AlterModelOptions(
            name='collectionprovider',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='conference',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='institution',
            options={'permissions': (('view_institutional_metrics', 'Can access metrics endpoints for their Institution'),)},
        ),
        migrations.AlterModelOptions(
            name='osfuser',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='preprint',
            options={'permissions': (('read_preprint', 'Can read the preprint'), ('write_preprint', 'Can write the preprint'), ('admin_preprint', 'Can manage the preprint'))},
        ),
        migrations.AlterModelOptions(
            name='preprintprovider',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='providerassetfile',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='registration',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='registrationprovider',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='scheduledbanner',
            options={'permissions': ()},
        ),
        migrations.AlterModelOptions(
            name='subject',
            options={'base_manager_name': 'objects', 'permissions': ()},
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='access_requests_enabled',
            field=models.BooleanField(blank=True, db_index=True, default=True, null=True),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='branched_from_node',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='external_registration',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='moderation_state',
            field=models.CharField(choices=[('undefined', 'Undefined'), ('initial', 'Initial'), ('reverted', 'Reverted'), ('pending', 'Pending'), ('rejected', 'Rejected'), ('accepted', 'Accepted'), ('embargo', 'Embargo'), ('pending_embargo_termination', 'PendingEmbargoTermination'), ('pending_withdraw_request', 'PendingWithdrawRequest'), ('pending_withdraw', 'PendingWithdraw'), ('withdrawn', 'Withdrawn')], default='initial', max_length=30),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='registered_meta',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
        migrations.AlterField(
            model_name='abstractnode',
            name='registration_responses_migrated',
            field=models.BooleanField(blank=True, db_index=True, default=True, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='additional_providers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=200), blank=True, default=list, size=None),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='allow_bulk_uploads',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='allow_updates',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='bulk_upload_auto_approval',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='preprint_word',
            field=models.CharField(choices=[('preprint', 'Preprint'), ('paper', 'Paper'), ('thesis', 'Thesis'), ('work', 'Work'), ('none', 'None')], default='preprint', max_length=10),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='reviews_comments_anonymous',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='reviews_comments_private',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='abstractprovider',
            name='subjects_acceptable',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=list, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
        migrations.AlterField(
            model_name='basefilenode',
            name='is_root',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='collection',
            name='collected_types',
            field=models.ManyToManyField(limit_choices_to={'model__in': ['abstractnode', 'basefilenode', 'collection', 'preprint']}, related_name='_osf_collection_collected_types_+', to='contenttypes.ContentType'),
        ),
        migrations.AlterField(
            model_name='draftregistration',
            name='registration_responses_migrated',
            field=models.BooleanField(blank=True, db_index=True, default=True, null=True),
        ),
        migrations.AlterField(
            model_name='preprint',
            name='ever_public',
            field=models.BooleanField(blank=True, default=False),
        ),
        migrations.AlterField(
            model_name='preprint',
            name='has_coi',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
