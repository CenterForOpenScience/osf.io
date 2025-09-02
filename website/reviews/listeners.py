from django.utils import timezone

from website.settings import DOMAIN, OSF_PREPRINTS_LOGO, OSF_REGISTRIES_LOGO
from website.reviews import signals as reviews_signals

@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context, user, resource):
    context['referrer_fullname'] = user.fullname
    provider = resource.provider
    from osf.models import NotificationType

    context['message'] = f'has requested withdrawal of "{resource.title}".'
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'

    for recipient in provider.get_group('moderator').user_set.all():
        context['user_fullname'] = recipient.fullname
        context['recipient_fullname'] = recipient.fullname

        NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.instance.emit(
            user=recipient,
            subscribed_object=provider,
            event_context=context,
            is_digest=True,
        )

@reviews_signals.reviews_email_withdrawal_requests.connect
def reviews_withdrawal_requests_notification(self, timestamp, context):
    preprint = context.pop('reviewable')
    context['reviewable_absolute_url'] = preprint.absolute_url
    context['reviewable_title'] = preprint.title
    context['reviewable__id'] = preprint._id
    from osf.models import NotificationType

    preprint_word = preprint.provider.preprint_word
    context['message'] = f'has requested withdrawal of the {preprint_word} "{preprint.title}".'
    context['reviews_submission_url'] = f'{DOMAIN}reviews/preprints/{preprint.provider._id}/{preprint._id}'

    for recipient in preprint.provider.subscribed_object.get_group('moderator').user_set.all():
        context['user_fullname'] = recipient.fullname
        context['recipient_fullname'] = recipient.fullname

        NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.instance.emit(
            user=recipient,
            event_context=context,
            subscribed_object=preprint.provider,
            is_digest=True,
        )

@reviews_signals.reviews_email_submit_moderators_notifications.connect
def reviews_submit_notification_moderators(self, timestamp, resource, context):
    """
    Handle email notifications to notify moderators of new submissions or resubmission.
    """
    # imports moved here to avoid AppRegistryNotReady error

    provider = resource.provider
    context['reviews_submission_url'] = (
        f'{DOMAIN}reviews/preprints/{provider._id}/{resource._id}'
    )
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

    from osf.models import NotificationType
    context['requester_contributor_names'] = ''.join(resource.contributors.values_list('fullname', flat=True))
    context['localized_timestamp'] = str(timezone.now())

    for recipient in resource.provider.get_group('moderator').user_set.all():
        context['recipient_fullname'] = recipient.fullname
        context['user_fullname'] = recipient.fullname

        NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.instance.emit(
            user=recipient,
            subscribed_object=provider,
            event_context=context,
            is_digest=True,
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

    context['no_future_emails'] = resource.provider.allow_submissions
    context['is_request_email'] = False
    context['requester_fullname'] = resource.actions.last().creator.fullname

    for recipient in recipients:
        context['is_creator'] = recipient == resource.creator
        context['provider_name'] = resource.provider.name
        context['user_username'] = recipient.username
        notification_type.instance.emit(
            user=recipient,
            subscribed_object=provider,
            event_context=context,
            is_digest=True,
        )
