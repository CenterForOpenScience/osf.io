from website.notifications.utils import subscribe_user_to_notifications
from website.project.signals import contributor_added, project_created

@project_created.connect
def subscribe_creator(node):
    subscribe_user_to_notifications(node, node.creator)

@contributor_added.connect
def subscribe_contributor(node, contributor, auth=None):
    subscribe_user_to_notifications(node, contributor)
