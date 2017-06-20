# -*- coding: utf-8 -*-
# This is an auto-migration and not a management command because:
#   1. The next script would fail if duplicate records existed
#   2. This should only need to be run once
from __future__ import unicode_literals
import logging

from django.db import connection, migrations

logger = logging.getLogger(__file__)

def remove_duplicate_notificationsubscriptions(state, schema):
    NotificationSubscription = state.get_model('osf', 'notificationsubscription')
    # Deletes the newest from each set of duplicates
    sql = """
    SELECT MAX(id)
    FROM osf_notificationsubscription
    GROUP BY _id HAVING COUNT(*) > 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        ids = list(sum(cursor.fetchall(), ()))
        logger.info('Deleting duplicate NotificationSubscriptions with `id`s {}'.format(ids))
        # Use Django to cascade delete through tables
        NotificationSubscription.objects.filter(id__in=ids).delete()

def noop(*args):
    logger.info('Removal of duplicates cannot be reversed, skipping.')

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0020_auto_20170426_0920'),
    ]

    operations = [
        migrations.RunPython(
            remove_duplicate_notificationsubscriptions, noop
        ),
    ]
