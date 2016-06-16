import logging
from website.notifications.exceptions import InvalidSubscriptionError
from website.notifications.utils import subscribe_user_to_notifications
from website.project.signals import contributor_added, project_created
from website.project.views.contributor import notify_added_contributor

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(node):
    try:
        subscribe_user_to_notifications(node, node.creator)
    except InvalidSubscriptionError as err:
        user = node.creator._id if node.creator else 'None'
        logger.warn('Skipping subscription of user {} to node {}'.format(user, node._id))
        logger.warn('Reason: {}'.format(str(err)))

@contributor_added.connect
def subscribe_contributor(node, contributor, auth=None, *args, **kwargs):
    try:
        subscribe_user_to_notifications(node, contributor)
    except InvalidSubscriptionError as err:
        logger.warn('Skipping subscription of user {} to node {}'.format(contributor, node._id))
        logger.warn('Reason: {}'.format(str(err)))
    else:
        notify_added_contributor(node, contributor, auth)
