from website.reviews import signals as reviews_signals
from website.settings import OSF_PREPRINTS_LOGO, OSF_REGISTRIES_LOGO, DOMAIN
from osf.models import NotificationType

@reviews_signals.reviews_email_submit.connect
def reviews_submit_notification(self, recipients, context, template=None):
    """
    Handle notifications for a new submission or resubmission (creator confirmation).
    """
    provider = context['reviewable'].provider

    if provider._id == 'osf':
        if provider.type == 'osf.preprintprovider':
            context['logo'] = OSF_PREPRINTS_LOGO
        elif provider.type == 'osf.registrationprovider':
            context['logo'] = OSF_REGISTRIES_LOGO
        else:
            raise NotImplementedError()
    else:
        context['logo'] = provider._id

    notification_type = NotificationType.objects.get(
        name=NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
    )

    for recipient in recipients:
        notification_type.emit(
            user=recipient,
            subscribed_object=provider,
            event_context=context
        )


@reviews_signals.reviews_email_submit_moderators_notifications.connect
def reviews_submit_notification_moderators(self, timestamp, context):
    """
    Notify moderators of new submissions or resubmissions.
    """
    from website.profile.utils import get_profile_image_url

    resource = context['reviewable']
    provider = resource.provider

    if provider.type == 'osf.preprintprovider':
        context['reviews_submission_url'] = f'{DOMAIN}reviews/preprints/{provider._id}/{resource._id}'
    elif provider.type == 'osf.registrationprovider':
        context['reviews_submission_url'] = f'{DOMAIN}{resource._id}?mode=moderator'
    else:
        raise NotImplementedError(f'unsupported provider type {provider.type}')

    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    revision_id = context.get('revision_id')
    if revision_id:
        context['message'] = f'submitted updates to "{resource.title}".'
        context['reviews_submission_url'] += f'&revisionId={revision_id}'
    else:
        context['message'] = f'resubmitted "{resource.title}".' if context.get('resubmission') else f'submitted "{resource.title}".'

    notification_type = NotificationType.objects.get(
        name=NotificationType.Type.PROVIDER_REVIEWS_MODERATOR_SUBMISSION_CONFIRMATION
    )

    subscriptions = notification_type.notificationsubscription_set.filter(
        subscribed_object=provider
    ).select_related('user')

    for subscription in subscriptions:
        subscription.emit(
            user=subscription.user,
            subscribed_object=provider,
            event_context=context
        )


@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context):
    """
    Notify moderators of new withdrawal requests.
    """
    from website.profile.utils import get_profile_image_url

    resource = context['reviewable']
    provider = resource.provider

    context['message'] = f'has requested withdrawal of "{resource.title}".'
    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'

    notification_type = NotificationType.objects.get(
        name=NotificationType.Type.PROVIDER_REVIEWS_MODERATOR_SUBMISSION_CONFIRMATION
    )

    subscriptions = notification_type.notificationsubscription_set.filter(
        subscribed_object=provider
    ).select_related('user')

    for subscription in subscriptions:
        subscription.emit(
            user=subscription.user,
            subscribed_object=provider,
            event_context=context
        )


@reviews_signals.reviews_email_withdrawal_requests.connect
def reviews_withdrawal_requests_notification(self, timestamp, context):
    """
    Notify moderators of withdrawal requests (preprint context).
    """
    from website.profile.utils import get_profile_image_url
    from website import settings

    preprint = context['reviewable']
    provider = preprint.provider
    preprint_word = provider.preprint_word

    context['message'] = f'has requested withdrawal of the {preprint_word} "{preprint.title}".'
    context['profile_image_url'] = get_profile_image_url(context['requester'])
    context['reviews_submission_url'] = f'{settings.DOMAIN}reviews/preprints/{provider._id}/{preprint._id}'

    notification_type = NotificationType.objects.get(
        name=NotificationType.Type.PROVIDER_REVIEWS_MODERATOR_SUBMISSION_CONFIRMATION
    )

    subscriptions = notification_type.notificationsubscription_set.filter(
        subscribed_object=provider
    ).select_related('user')

    for subscription in subscriptions:
        subscription.emit(
            user=subscription.user,
            subscribed_object=provider,
            event_context=context
        )
