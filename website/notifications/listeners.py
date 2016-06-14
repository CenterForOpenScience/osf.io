from website.notifications.utils import subscribe_user_to_notifications
from website.project.signals import contributor_added, project_created
from website.project.views.contributor import notify_added_contributor

@project_created.connect
def subscribe_creator(node):
    subscribe_user_to_notifications(node, node.creator)

@contributor_added.connect
def subscribe_contributor(node, contributor, auth=None, *args, **kwargs):
    subscribe_user_to_notifications(node, contributor)
    notify_added_contributor(node, contributor, auth)
