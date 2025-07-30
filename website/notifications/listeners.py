import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from osf.models import NotificationSubscription, NotificationType
from website.project.signals import contributor_added, project_created
from framework.auth.signals import user_confirmed
from website.project.signals import privacy_set_public
from website import settings

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(resource):
    if resource.is_collection or resource.is_deleted:
        return None
    user = resource.creator
    if user.is_registered:
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type__name=NotificationType.Type.USER_FILE_UPDATED,
        )
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type__name=NotificationType.Type.FILE_UPDATED,
            object_id=resource.id,
            content_type=ContentType.objects.get_for_model(resource)
        )

@contributor_added.connect
def subscribe_contributor(resource, contributor, auth=None, *args, **kwargs):
    from osf.models import Node
    if isinstance(resource, Node):
        if resource.is_collection or resource.is_deleted:
            return None
    if contributor.is_registered:
        NotificationSubscription.objects.get_or_create(
            user=contributor,
            notification_type__name=NotificationType.Type.USER_FILE_UPDATED,
        )
        NotificationSubscription.objects.get_or_create(
            user=contributor,
            notification_type__name=NotificationType.Type.FILE_UPDATED,
            object_id=resource.id,
            content_type=ContentType.objects.get_for_model(resource)
        )

@user_confirmed.connect
def subscribe_confirmed_user(user):
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    NotificationType = apps.get_model('osf.NotificationType')
    NotificationSubscription.objects.get_or_create(
        user=user,
        notification_type=NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
    )
    NotificationSubscription.objects.get_or_create(
        user=user,
        notification_type=NotificationType.objects.get(name=NotificationType.Type.USER_REVIEWS)
    )


@privacy_set_public.connect
def queue_first_public_project_email(user, node):
    """Queue and email after user has made their first
    non-OSF4M project public.
    """
    NotificationType.objects.get(
        name=NotificationType.Type.USER_NEW_PUBLIC_PROJECT,
    ).emit(
        user=user,
        event_context={
            'node': node,
            'user': user,
            'nid': node._id,
            'fullname': user.fullname,
            'project_title': node.title,
            'osf_support_email': settings.OSF_SUPPORT_EMAIL,
        }
    )
