import logging

from django.apps import apps

from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import run_postcommit
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
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED),
            _is_digest=True,
        )
        NotificationSubscription.objects.get_or_create(
            user=user,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED),
            object_id=resource.id,
            content_type=ContentType.objects.get_for_model(resource),
            _is_digest=True,
        )

@contributor_added.connect
def subscribe_contributor(resource, contributor, auth=None, *args, **kwargs):
    from django.contrib.contenttypes.models import ContentType
    from osf.models import NotificationSubscription, NotificationType

    from osf.models import Node
    if isinstance(resource, Node):
        if resource.is_collection or resource.is_deleted:
            return None
    if contributor.is_registered:
        NotificationSubscription.objects.get_or_create(
            user=contributor,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED),
            _is_digest=True,
        )
        NotificationSubscription.objects.get_or_create(
            user=contributor,
            notification_type=NotificationType.objects.get(name=NotificationType.Type.FILE_UPDATED),
            object_id=resource.id,
            content_type=ContentType.objects.get_for_model(resource),
            _is_digest=True,
        )


@reviews_signals.reviews_email_submit_moderators_notifications.connect
def reviews_submit_notification_moderators(self, timestamp, context, resource):
    """
    Handle email notifications to notify moderators of new submissions or resubmission.
    """

    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationType
    from website.settings import DOMAIN

    provider = resource.provider
    context['domain'] = DOMAIN

    # Set submission url
    if provider.type == 'osf.preprintprovider':
        context['reviews_submission_url'] = (
            f'{DOMAIN}reviews/preprints/{provider._id}/{resource._id}'
        )
    elif provider.type == 'osf.registrationprovider':
        context['reviews_submission_url'] = f'{DOMAIN}{resource._id}?mode=moderator'
    else:
        raise NotImplementedError(f'unsupported provider type {provider.type}')

    # Set message
    revision_id = context.get('revision_id')
    if revision_id:
        context['message'] = f'submitted updates to "{resource.title}".'
        context['reviews_submission_url'] += f'&revisionId={revision_id}'
    else:
        if context.get('resubmission'):
            context['message'] = f'resubmitted "{resource.title}".'
        else:
            context['message'] = f'submitted "{resource.title}".'

    for recipient in resource.provider.get_group('moderator').user_set.all():
        context['user_fullname'] = recipient.fullname
        context['recipient_fullname'] = recipient.fullname

        NotificationType.objects.get(
            name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        ).emit(
            user=recipient,
            subscribed_object=provider,
            event_context=context,
            is_digest=True,
        )

# Handle email notifications to notify moderators of new submissions.
@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context, user, resource):
    from website.settings import DOMAIN
    from osf.models import NotificationType

    provider = resource.provider
    # Set message
    context['message'] = f'has requested withdrawal of "{resource.title}".'
    # Set submission url
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'
    NotificationType.objects.get(
        name=NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
    ).emit(
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
    remove_subscription_task(node._id)

@node_deleted.connect
def remove_supplemental_node(node):
    remove_supplemental_node_from_preprints(node._id)

@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_subscription_task(node_id):
    from django.contrib.contenttypes.models import ContentType
    AbstractNode = apps.get_model('osf.AbstractNode')
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    node = AbstractNode.load(node_id)
    NotificationSubscription.objects.filter(
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node),
    ).delete()


@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def remove_supplemental_node_from_preprints(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')

    node = AbstractNode.load(node_id)
    for preprint in node.preprints.all():
        if preprint.node is not None:
            preprint.node = None
            preprint.save()
