import osf
from django.db import migrations, models
from django.conf import settings
import django_extensions.db.fields
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0029_remove_abstractnode_keenio_read_key'),
    ]

    operations = [
        migrations.RunSQL(
            """
            DO $$
            DECLARE
                idx record;
            BEGIN
                FOR idx IN
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'osf_notificationsubscription'
                LOOP
                    EXECUTE format(
                        'ALTER INDEX %I RENAME TO %I',
                        idx.indexname,
                        replace(idx.indexname, 'osf_notificationsubscription', 'osf_notificationsubscription_legacy')
                    );
                END LOOP;
            END$$;
            """
        ),
        migrations.AlterModelTable(
            name='NotificationSubscription',
            table='osf_notificationsubscription_legacy',
        ),

        migrations.RenameModel(
            old_name='NotificationSubscription',
            new_name='NotificationSubscriptionLegacy',
        ),
        migrations.CreateModel(
            name='NotificationType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('notification_freq', models.CharField(
                    choices=[('none', 'None'), ('instantly', 'Instantly'), ('daily', 'Daily'), ('weekly', 'Weekly'),
                             ('monthly', 'Monthly')], default='instantly', max_length=32)),
                ('template', models.TextField(
                    help_text='Template used to render the event_info. Supports Django template syntax.')),
                ('object_content_type', models.ForeignKey(blank=True,
                                                          help_text='Content type for subscribed objects. Null means global event.',
                                                          null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                          to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Notification Type',
                'verbose_name_plural': 'Notification Types',
            },
        ),
        migrations.CreateModel(
            name='NotificationSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created',
                 django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified',
                 django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('message_frequency', models.CharField(max_length=32)),
                ('object_id', models.CharField(blank=True, max_length=255, null=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                                   to='contenttypes.contenttype')),
                ('notification_type',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='osf.notificationtype')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification Subscription',
                'verbose_name_plural': 'Notification Subscriptions',
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_context', models.JSONField()),
                ('sent', models.DateTimeField(blank=True, null=True)),
                ('seen', models.DateTimeField(blank=True, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('subscription',
                 models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications',
                                   to='osf.notificationsubscription')),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
            },
        )
    ]
