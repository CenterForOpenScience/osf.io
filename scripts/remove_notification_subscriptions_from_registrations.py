""" Script for removing NotificationSubscriptions from registrations.
    Registrations shouldn't have them!
"""
import logging
import sys

import django
django.setup()

from website.app import init_app
from django.apps import apps

logger = logging.getLogger(__name__)


def remove_notification_subscriptions_from_registrations(dry_run=True):
    Registration = apps.get_model('osf.Registration')
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')

    notifications_to_delete = NotificationSubscription.objects.filter(node__type='osf.registration')
    registrations_affected = Registration.objects.filter(
        id__in=notifications_to_delete.values_list(
            'node_id', flat=True
        )
    )
    logger.info('{} NotificationSubscriptions will be deleted.'.format(notifications_to_delete.count()))
    logger.info('{} Registrations will be affected: {}'.format(
        registrations_affected.count(),
        list(registrations_affected.values_list('guids___id', flat=True)))
    )

    if not dry_run:
        notifications_to_delete.delete()
        logger.info('Registration Notification Subscriptions removed.')

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    init_app(routes=False)
    remove_notification_subscriptions_from_registrations(dry_run=dry_run)
