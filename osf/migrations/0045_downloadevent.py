import django.db.models.deletion
from django.db import migrations, models

from osf.admin import DASHBOARD_GROUP_NAME


DASHBOARD_USERS = [
    'sheredko.andriy@gmail.com',
    'bodintsov@exoft.net',
    'isokhan@exoft.net',
    'ykopka@exoft.net',
    'bgeiger@cos.io',
    'osmand@cos.io',
    'ramya@cos.io',
    'eric@cos.io',
]


def create_dashboard_group(apps, schema_editor):
    """Create the allow-list group the dashboard loads against and seed it.

    The group carries no permissions of its own — membership is the only gate.
    """
    Group = apps.get_model('auth', 'Group')
    OSFUser = apps.get_model('osf', 'OSFUser')
    group, _ = Group.objects.get_or_create(name=DASHBOARD_GROUP_NAME)
    for username in DASHBOARD_USERS:
        user = OSFUser.objects.filter(username=username).first()
        if user:
            group.user_set.add(user)


def remove_dashboard_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=DASHBOARD_GROUP_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0044_notification_scheduled'),
    ]

    operations = [
        migrations.CreateModel(
            name='DownloadEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('resource_guid', models.CharField(blank=True, db_index=True, default='', max_length=255)),
                ('path', models.TextField(blank=True, default='')),
                ('download_type', models.CharField(choices=[('file', 'Single file'), ('folder_zip', 'Folder zip'), ('project', 'Whole-project zip')], max_length=16)),
                ('zip_completed', models.BooleanField(blank=True, null=True)),
                ('size_bytes', models.BigIntegerField(blank=True, null=True)),
                ('storage_region', models.CharField(blank=True, default='', max_length=64)),
                ('user_region', models.CharField(blank=True, default='', max_length=64)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('source_area', models.CharField(blank=True, default='', max_length=128)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='download_events', to='osf.osfuser')),
            ],
        ),
        migrations.AddIndex(
            model_name='downloadevent',
            index=models.Index(fields=['created', 'download_type'], name='download_event_crt_type'),
        ),
        migrations.AddIndex(
            model_name='downloadevent',
            index=models.Index(fields=['created', 'storage_region'], name='download_event_crt_regn'),
        ),
        migrations.AddIndex(
            model_name='downloadevent',
            index=models.Index(fields=['created', 'user_region'], name='download_event_crt_user'),
        ),
        migrations.RunPython(create_dashboard_group, remove_dashboard_group),
    ]
