# Generated by Django 3.2.15 on 2022-10-28 17:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base
import osf.utils.workflows


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0004_django3_upgrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectionsubmission',
            name='machine_state',
            field=models.IntegerField(choices=[(0, 'Undefined'), (1, 'Unapproved'), (2, 'PendingModeration'), (3, 'Approved'), (4, 'Rejected'), (5, 'ModeratorRejected'), (6, 'Completed'), (7, 'InProgress')], default=osf.utils.workflows.CollectionSubmissionStates['IN_PROGRESS']),
        ),
        migrations.CreateModel(
            name='CollectionSubmissionAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('comment', models.TextField(blank=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('auto', models.BooleanField(default=False)),
                ('trigger', models.IntegerField(choices=[('submit', 'Submit'), ('approve', 'Approve'), ('reject', 'Reject'), ('admin_remove', 'AdminRemove'), ('moderator_remove', 'ModeratorRemove')])),
                ('from_state', models.IntegerField(choices=[('undefined', 'Undefined'), ('unapproved', 'Unapproved'), ('pending_moderation', 'PendingModeration'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('moderator_rejected', 'ModeratorRejected'), ('completed', 'Completed'), ('in_progress', 'InProgress')])),
                ('to_state', models.IntegerField(choices=[('undefined', 'Undefined'), ('unapproved', 'Unapproved'), ('pending_moderation', 'PendingModeration'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('moderator_rejected', 'ModeratorRejected'), ('completed', 'Completed'), ('in_progress', 'InProgress')])),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='osf.collectionsubmission')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
    ]
