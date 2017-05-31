"""
This migration subscribes each user to USER_SUBSCRIPTIONS_AVAILABLE if a subscription
does not already exist.
"""

import logging
import sys

from django.apps import apps
from django.db import transaction
from website.app import init_app
from website.notifications.model import NotificationSubscription
from website.notifications import constants
from website.notifications.utils import to_subscription_key

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)

def add_global_subscriptions(dry=True):
    OSFUser = apps.get_model('osf.OSFUser')
    notification_type = 'email_transactional'
    user_events = constants.USER_SUBSCRIPTIONS_AVAILABLE

    count = 0

    with transaction.atomic():
        for user in OSFUser.objects.filter(is_registered=True, date_confirmed__isnull=False):
            changed = False
            if not user.is_active:
                continue
            for user_event in user_events:
                user_event_id = to_subscription_key(user._id, user_event)

                subscription = NotificationSubscription.load(user_event_id)
                if not subscription:
                    logger.info('No {} subscription found for user {}. Subscribing...'.format(user_event, user._id))
                    subscription = NotificationSubscription(_id=user_event_id, owner=user, event_name=user_event)
                    subscription.save()  # Need to save in order to access m2m fields
                    subscription.add_user_to_subscription(user, notification_type)
                    subscription.save()
                    changed = True
                else:
                    logger.info('User {} already has a {} subscription'.format(user._id, user_event))
            if changed:
                count += 1

        logger.info('Added subscriptions for {} users'.format(count))
        if dry:
            raise RuntimeError('Dry mode -- rolling back transaction')

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    init_app(routes=False)
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    add_global_subscriptions(dry=dry)
