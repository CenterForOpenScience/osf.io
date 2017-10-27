# -*- coding: utf-8 -*-
# This is a management command, rather than a migration script, for two primary reasons:
#   1. It makes no changes to database structure (e.g. AlterField), only database content.
#   2. It takes a long time to run and the site doesn't need to be down that long.

from __future__ import unicode_literals
import logging

import django
django.setup()

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import OSFUser, NotificationSubscription

from website.notifications.utils import to_subscription_key

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def add_reviews_notification_setting(notification_type):
    active_users = OSFUser.objects.filter(date_confirmed__isnull=False).exclude(date_disabled__isnull=False).exclude(is_active=False).order_by('id')
    total_active_users = active_users.count()

    logger.info('About to add a global_reviews setting for {} users.'.format(total_active_users))

    total_created = 0
    for user in active_users.iterator():
        user_subscription_id = to_subscription_key(user._id, notification_type)

        subscription = NotificationSubscription.load(user_subscription_id)
        if not subscription:
            logger.info('No {} subscription found for user {}. Subscribing...'.format(notification_type, user._id))
            subscription = NotificationSubscription(_id=user_subscription_id, owner=user, event_name=notification_type)
            subscription.save()  # Need to save in order to access m2m fields
            subscription.add_user_to_subscription(user, 'email_transactional')
        else:
            logger.info('User {} already has a {} subscription'.format(user._id, notification_type))
        total_created += 1

    logger.info('Added subscriptions for {}/{} users'.format(total_created, total_active_users))


class Command(BaseCommand):
    """
    Add subscription to all active users for given notification type.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

        parser.add_argument(
            '--notification',
            type=str,
            required=True,
            help='Notification type to subscribe users to',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            add_reviews_notification_setting(notification_type=options['notification'])
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
