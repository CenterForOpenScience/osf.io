import logging
from website.project.signals import contributor_added, project_created
from framework.auth.signals import user_confirmed

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(node):
    if node.is_collection or node.is_deleted:
        return None
    from website.notifications.utils import subscribe_user_to_notifications
    subscribe_user_to_notifications(node, node.creator)

@contributor_added.connect
def subscribe_contributor(node, contributor, auth=None, *args, **kwargs):
    from website.notifications.utils import subscribe_user_to_notifications
    subscribe_user_to_notifications(node, contributor)

@user_confirmed.connect
def subscribe_confirmed_user(user):
    from website.notifications.utils import subscribe_user_to_global_notifications
    subscribe_user_to_global_notifications(user)
