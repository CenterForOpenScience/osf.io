import logging

from django.apps import apps

from website.project.signals import contributor_added, project_created, node_deleted, contributor_removed
from website.reviews import signals as reviews_signals

logger = logging.getLogger(__name__)

@project_created.connect
def subscribe_creator(resource):
    from osf.models import NotificationSubscription, NotificationType

    from django.contrib.contenttypes.models import ContentType

    if resource.is_collection or resource.is_deleted:
        return None
    user = resource.creator
    if user.is_registered:
        try:
            NotificationSubscription.objects.get_or_create(
                user=user,
                notification_type=NotificationType.Type.USER_FILE_UPDATED.instance,
                object_id=user.id,
                content_type=ContentType.objects.get_for_model(user),
                _is_digest=True,
                message_frequency='instantly',
            )
        except NotificationSubscription.MultipleObjectsReturned:
            pass
        try:
            NotificationSubscription.objects.get_or_create(
                user=user,
                notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance,
                object_id=resource.id,
                content_type=ContentType.objects.get_for_model(resource),
                _is_digest=True,
                message_frequency='instantly',
            )
        except NotificationSubscription.MultipleObjectsReturned:
            pass

@contributor_added.connect
def subscribe_contributor(resource, contributor, auth=None, *args, **kwargs):
    from django.contrib.contenttypes.models import ContentType
    from osf.models import NotificationSubscription, NotificationType

    from osf.models import Node
    if isinstance(resource, Node):
        if resource.is_collection or resource.is_deleted:
            return None

    if contributor.is_registered:
        try:
            NotificationSubscription.objects.get_or_create(
                user=contributor,
                notification_type=NotificationType.Type.USER_FILE_UPDATED.instance,
                object_id=contributor.id,
                content_type=ContentType.objects.get_for_model(contributor),
                _is_digest=True,
                message_frequency='instantly',
            )
        except NotificationSubscription.MultipleObjectsReturned:
            pass
        try:
            NotificationSubscription.objects.get_or_create(
                user=contributor,
                notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance,
                object_id=resource.id,
                content_type=ContentType.objects.get_for_model(resource),
                _is_digest=True,
                message_frequency='instantly',
            )
        except NotificationSubscription.MultipleObjectsReturned:
            pass


# Handle email notifications to notify moderators of new submissions.
@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context, user, resource):
    from website.settings import DOMAIN
    from osf.models import NotificationType

    provider = resource.provider
    context['provider_id'] = provider.id
    # Set message
    context['message'] = f'has requested withdrawal of "{resource.title}".'
    # Set submission url
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'
    context['localized_timestamp'] = str(timestamp)
    NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.instance.emit(
        subscribed_object=provider,
        user=user,
        event_context=context
    )


@contributor_removed.connect
def remove_contributor_from_subscriptions(node, user):
    """ Remove contributor from node subscriptions unless the user is an
        admin on any of node's parent projects.
    """
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    from django.contrib.contenttypes.models import ContentType

    Preprint = apps.get_model('osf.Preprint')
    DraftRegistration = apps.get_model('osf.DraftRegistration')
    # Preprints don't have subscriptions at this time
    if isinstance(node, Preprint):
        return
    if isinstance(node, DraftRegistration):
        return

    # If user still has permissions through being a contributor or group member, or has
    # admin perms on a parent, don't remove their subscription
    if not (node.is_contributor_or_group_member(user)) and user._id not in node.admin_contributor_or_group_member_ids:
        node_subscriptions = NotificationSubscription.objects.filter(
            user=user,
            user__isnull=True,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node)
        )

        for subscription in node_subscriptions:
            subscription.delete()


@node_deleted.connect
def remove_subscription(node):
    from notifications.tasks import remove_subscription_task
    remove_subscription_task(node._id)

@node_deleted.connect
def remove_supplemental_node(node):
    from notifications.tasks import remove_supplemental_node_from_preprints

    remove_supplemental_node_from_preprints(node._id)
