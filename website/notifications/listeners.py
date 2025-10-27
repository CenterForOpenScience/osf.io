import logging
from website.notifications.exceptions import InvalidSubscriptionError
from website.notifications.utils import subscribe_user_to_notifications, subscribe_user_to_global_notifications
from website.project.signals import contributor_added, project_created
from framework.auth.signals import user_confirmed

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(node):
    if node.is_collection or node.is_deleted:
        return None
    try:
        subscribe_user_to_notifications(node, node.creator)
    except InvalidSubscriptionError as err:
        user = node.creator._id if node.creator else 'None'
        logger.warning(f'Skipping subscription of user {user} to node {node._id}')
        logger.warning(f'Reason: {str(err)}')

@contributor_added.connect
def subscribe_contributor(node, contributor, auth=None, *args, **kwargs):
    try:
        subscribe_user_to_notifications(node, contributor)
    except InvalidSubscriptionError as err:
        logger.warning(f'Skipping subscription of user {contributor} to node {node._id}')
        logger.warning(f'Reason: {str(err)}')

@user_confirmed.connect
def subscribe_confirmed_user(user):
    try:
        subscribe_user_to_global_notifications(user)
    except InvalidSubscriptionError as err:
        logger.warning(f'Skipping subscription of user {user} to global subscriptions')
        logger.warning(f'Reason: {str(err)}')
