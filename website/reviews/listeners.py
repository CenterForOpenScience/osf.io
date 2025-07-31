from django.contrib.contenttypes.models import ContentType

from osf.models import NotificationType
from website.settings import DOMAIN, OSF_PREPRINTS_LOGO, OSF_REGISTRIES_LOGO
from website.reviews import signals as reviews_signals

@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context, user, resource):
    context['referrer_fullname'] = user.fullname
    provider = resource.provider
    from django.contrib.contenttypes.models import ContentType
    from osf.models import NotificationSubscription, NotificationType

    provider_subscription, _ = NotificationSubscription.objects.get_or_create(
        notification_type__name=NotificationType.Type.PROVIDER_REVIEWS_WITHDRAWAL_REQUESTED,
        object_id=provider.id,
        content_type=ContentType.objects.get_for_model(provider.__class__),
    )

    context['message'] = f'has requested withdrawal of "{resource.title}".'
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'

    for recipient in provider_subscription.subscribed_object.get_group('moderator').user_set.all():
        NotificationType.objects.get(
            name=NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS
        ).emit(
            user=recipient,
            event_context=context,
        )

@reviews_signals.reviews_email_withdrawal_requests.connect
def reviews_withdrawal_requests_notification(self, timestamp, context):
    preprint = context['reviewable']
    preprint_word = preprint.provider.preprint_word
    from django.contrib.contenttypes.models import ContentType
    from osf.models import NotificationSubscription, NotificationType

    provider_subscription, _ = NotificationSubscription.objects.get_or_create(
        notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS,
        object_id=preprint.provider.id,
        content_type=ContentType.objects.get_for_model(preprint.provider.__class__),
    )
    context['message'] = f'has requested withdrawal of the {preprint_word} "{preprint.title}".'
    context['reviews_submission_url'] = f'{DOMAIN}reviews/preprints/{preprint.provider._id}/{preprint._id}'

    for recipient in provider_subscription.subscribed_object.get_group('moderator').user_set.all():
        NotificationType.objects.get(
            name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        ).emit(
            user=recipient,
            event_context=context,
        )

@reviews_signals.reviews_email_submit_moderators_notifications.connect
def reviews_submit_notification_moderators(self, timestamp, resource, context):
    """
    Handle email notifications to notify moderators of new submissions or resubmission.
    """
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription

    provider = resource.provider

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

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription, created = NotificationSubscription.objects.get_or_create(
        notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS,
        object_id=provider.id,
        content_type=ContentType.objects.get_for_model(provider.__class__),
    )
    for recipient in provider_subscription.subscribed_object.get_group('moderator').user_set.all():
        NotificationType.objects.get(
            name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        ).emit(
            user=recipient,
            event_context=context,
        )


@reviews_signals.reviews_email_submit.connect
def reviews_submit_notification(self, recipients, context, resource, notification_type=None):
    """
    Handle email notifications for a new submission or a resubmission
    """
    provider = resource.provider
    if provider._id == 'osf':
        if provider.type == 'osf.preprintprovider':
            context['logo'] = OSF_PREPRINTS_LOGO
        elif provider.type == 'osf.registrationprovider':
            context['logo'] = OSF_REGISTRIES_LOGO
        else:
            raise NotImplementedError()
    else:
        context['logo'] = resource.provider._id

    for recipient in recipients:
        context['is_creator'] = recipient == resource.creator
        context['provider_name'] = resource.provider.name
        NotificationType.objects.get(
            name=notification_type
        ).emit(
            user=recipient,
            event_context=context
        )
