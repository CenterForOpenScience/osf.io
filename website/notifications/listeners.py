import logging

from django.apps import apps
from website.project.signals import contributor_added, project_created
from framework.auth.signals import user_confirmed

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(resource):
    if resource.is_collection or resource.is_deleted:
        return None
    from website.notifications.utils import subscribe_user_to_notifications
    subscribe_user_to_notifications(resource, resource.creator)

@contributor_added.connect
def subscribe_contributor(resource, contributor, auth=None, *args, **kwargs):
    from website.notifications.utils import subscribe_user_to_notifications
    from osf.models import Node

    if isinstance(resource, Node):
        if resource.is_collection or resource.is_deleted:
            return None
        subscribe_user_to_notifications(resource, contributor)

@user_confirmed.connect
def subscribe_confirmed_user(user):
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    NotificationType = apps.get_model('osf.NotificationType')
    user_events = [
        NotificationType.Type.USER_FILE_UPDATED,
        NotificationType.Type.USER_REVIEWS,
    ]
    for user_event in user_events:
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type__name=user_event
        )
