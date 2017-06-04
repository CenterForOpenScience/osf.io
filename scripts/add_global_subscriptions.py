"""
This migration subscribes each user to USER_SUBSCRIPTIONS_AVAILABLE if a subscription
does not already exist.
"""

import logging
import sys

from website.app import init_app
from website import models
from website.notifications.model import NotificationSubscription
from website.notifications import constants
from website.notifications.utils import to_subscription_key

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)

app = init_app()


def add_global_subscriptions():

    notification_type = 'email_transactional'
    user_events = constants.USER_SUBSCRIPTIONS_AVAILABLE

    for user in models.User.find():
        if user.is_active and user.is_registered:
            for user_event in user_events:
                user_event_id = to_subscription_key(user._id, user_event)

                subscription = NotificationSubscription.load(user_event_id)
                if not subscription:
                    subscription = NotificationSubscription(_id=user_event_id, owner=user, event_name=user_event)
                    subscription.add_user_to_subscription(user, notification_type)
                    subscription.save()
                    logger.info('No subscription found. {} created.'.format(subscription))
                else:
                    logger.info('Subscription {} found.'.format(subscription))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    add_global_subscriptions()
