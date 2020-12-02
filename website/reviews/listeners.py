
from django.utils import timezone

from website.notifications import utils
from website.mails import mails
from website.reviews import signals as reviews_signals
from website.settings import OSF_PREPRINTS_LOGO, OSF_REGISTRIES_LOGO, DOMAIN


# Handle email notifications including: update comment, accept, and reject of submission.
@reviews_signals.reviews_email.connect
def reviews_notification(self, creator, template, context, action):
    # Avoid AppRegistryNotReady error
    from website.notifications.emails import notify_global_event
    recipients = list(action.target.contributors)
    time_now = action.created if action is not None else timezone.now()
    node = action.target
    notify_global_event(
        event='global_reviews',
        sender_user=creator,
        node=node,
        timestamp=time_now,
        recipients=recipients,
        template=template,
        context=context
    )


# Handle email notifications for a new submission.
@reviews_signals.reviews_email_submit.connect
def reviews_submit_notification(self, recipients, context):
    # Avoid AppRegistryNotReady error
    from website.notifications.emails import get_user_subscriptions

    event_type = utils.find_subscription_type('global_reviews')

    provider = context['reviewable'].provider
    if provider._id == 'osf':
        if provider.type == 'osf.preprintprovider':
            context['logo'] = OSF_PREPRINTS_LOGO
        elif provider.type == 'osf.registrationprovider':
            context['logo'] = OSF_REGISTRIES_LOGO
        else:
            raise NotImplementedError()
    else:
        context['logo'] = context['reviewable'].provider._id

    for recipient in recipients:
        user_subscriptions = get_user_subscriptions(recipient, event_type)
        context['no_future_emails'] = user_subscriptions['none']
        context['is_creator'] = recipient == context['reviewable'].creator
        context['provider_name'] = context['reviewable'].provider.name
        mails.send_mail(
            recipient.username,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            mimetype='html',
            user=recipient,
            **context
        )


# Handle email notifications to notify moderators of new submissions.
@reviews_signals.reviews_email_submit_moderators_notifications.connect
def reviews_submit_notification_moderators(self, timestamp, context):
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription
    from website.profile.utils import get_profile_image_url
    from website.notifications.emails import store_emails

    resource = context['reviewable']
    provider = resource.provider

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription, created = NotificationSubscription.objects.get_or_create(
        _id=f'{provider._id}_new_pending_submissions',
        provider=provider
    )

    # Set message
    context['message'] = f'submitted "{resource.title}".'
    # Set url for profile image of the submitter
    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    # Set submission url
    if provider.type == 'osf.preprintprovider':
        url_segment = 'preprints'
        flag_suffix = ''
    elif provider.type == 'osf.registrationprovider':
        url_segment = 'registries'
        flag_suffix = '?mode=moderator'
    else:
        raise NotImplementedError(f'unsupported provider type {provider.type}')

    context['reviews_submission_url'] = f'{DOMAIN}reviews/{url_segment}/{provider._id}/{resource._id}{flag_suffix}'

    email_transactional_ids = list(provider_subscription.email_transactional.all().values_list('guids___id', flat=True))
    email_digest_ids = list(provider_subscription.email_digest.all().values_list('guids___id', flat=True))

    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    store_emails(
        email_transactional_ids,
        'email_transactional',
        'new_pending_submissions',
        context['referrer'],
        resource,
        timestamp,
        abstract_provider=provider,
        **context
    )

    # Store emails to be sent to subscribers daily
    store_emails(
        email_digest_ids,
        'email_digest',
        'new_pending_submissions',
        context['referrer'],
        resource,
        timestamp,
        abstract_provider=provider,
        **context
    )

# Handle email notifications to notify moderators of new submissions.
@reviews_signals.reviews_withdraw_requests_notification_moderators.connect
def reviews_withdraw_requests_notification_moderators(self, timestamp, context):
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription
    from website.profile.utils import get_profile_image_url
    from website.notifications.emails import store_emails

    resource = context['reviewable']
    provider = resource.provider

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription, created = NotificationSubscription.objects.get_or_create(
        _id=f'{provider._id}_new_pending_withdraw_requests',
        provider=provider
    )

    # Set message
    context['message'] = f'has requested withdrawal of "{resource.title}".'
    # Set url for profile image of the submitter
    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    # Set submission url
    context['reviews_submission_url'] = f'{DOMAIN}reviews/registries/{provider._id}/{resource._id}'

    email_transactional_ids = list(provider_subscription.email_transactional.all().values_list('guids___id', flat=True))
    email_digest_ids = list(provider_subscription.email_digest.all().values_list('guids___id', flat=True))

    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    store_emails(
        email_transactional_ids,
        'email_transactional',
        'new_pending_withdraw_requests',
        context['referrer'],
        resource,
        timestamp,
        abstract_provider=provider,
        template='new_pending_submissions',
        **context
    )

    # Store emails to be sent to subscribers daily
    store_emails(
        email_digest_ids,
        'email_digest',
        'new_pending_withdraw_requests',
        context['referrer'],
        resource,
        timestamp,
        abstract_provider=provider,
        template='new_pending_submissions',
        **context
    )

# Handle email notifications to notify moderators of new withdrawal requests
@reviews_signals.reviews_email_withdrawal_requests.connect
def reviews_withdrawal_requests_notification(self, timestamp, context):
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription
    from website.notifications.emails import store_emails
    from website.profile.utils import get_profile_image_url
    from website import settings

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription = NotificationSubscription.load(
        '{}_new_pending_submissions'.format(context['reviewable'].provider._id))
    preprint = context['reviewable']
    preprint_word = preprint.provider.preprint_word

    # Set message
    context['message'] = u'has requested withdrawal of the {} "{}".'.format(preprint_word, preprint.title)
    # Set url for profile image of the submitter
    context['profile_image_url'] = get_profile_image_url(context['requester'])
    # Set submission url
    context['reviews_submission_url'] = '{}reviews/preprints/{}/{}'.format(settings.DOMAIN,
                                                                           preprint.provider._id,
                                                                           preprint._id)

    email_transactional_ids = list(provider_subscription.email_transactional.all().values_list('guids___id', flat=True))
    email_digest_ids = list(provider_subscription.email_digest.all().values_list('guids___id', flat=True))

    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    store_emails(
        email_transactional_ids,
        'email_transactional',
        'new_pending_submissions',
        context['requester'],
        preprint,
        timestamp,
        abstract_provider=preprint.provider,
        **context
    )

    # Store emails to be sent to subscribers daily
    store_emails(
        email_digest_ids,
        'email_digest',
        'new_pending_submissions',
        context['requester'],
        preprint,
        timestamp,
        abstract_provider=preprint.provider,
        **context
    )
