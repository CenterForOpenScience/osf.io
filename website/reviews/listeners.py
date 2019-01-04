
from django.utils import timezone

from website.mails import mails
from website.notifications import utils
from website.reviews import signals as reviews_signals

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
    from website import settings

    event_type = utils.find_subscription_type('global_reviews')
    if context['reviewable'].provider._id == 'osf':
        context['logo'] = settings.OSF_PREPRINTS_LOGO
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
    from website.notifications import emails
    from website import settings

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription = NotificationSubscription.load('{}_new_pending_submissions'.format(context['reviewable'].provider._id))
    # Set message
    context['message'] = u'submitted "{}".'.format(context['reviewable'].title)
    # Set url for profile image of the submitter
    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    # Set submission url
    context['reviews_submission_url'] = '{}reviews/preprints/{}/{}'.format(settings.DOMAIN, context['reviewable'].provider._id, context['reviewable']._id)
    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    emails.store_emails(provider_subscription.email_transactional.all().values_list('guids___id', flat=True),
                        'email_transactional',
                        'new_pending_submissions',
                        context['referrer'],
                        context['reviewable'],
                        timestamp,
                        abstract_provider=context['reviewable'].provider,
                        **context)

    # Store emails to be sent to subscribers daily
    emails.store_emails(provider_subscription.email_digest.all().values_list('guids___id', flat=True),
                        'email_digest',
                        'new_pending_submissions',
                        context['referrer'],
                        context['reviewable'],
                        timestamp,
                        abstract_provider=context['reviewable'].provider,
                        **context)


# Handle email notifications to notify moderators of new withdrawal requests
@reviews_signals.reviews_email_withdrawal_requests.connect
def reviews_withdrawal_requests_notification(self, timestamp, context):
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription
    from website.profile.utils import get_profile_image_url
    from website.notifications import emails
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
    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    emails.store_emails(provider_subscription.email_transactional.all().values_list('guids___id', flat=True),
                        'email_transactional',
                        'new_pending_submissions',
                        context['requester'],
                        preprint,
                        timestamp,
                        abstract_provider=preprint.provider,
                        **context)

    # Store emails to be sent to subscribers daily
    emails.store_emails(provider_subscription.email_digest.all().values_list('guids___id', flat=True),
                        'email_digest',
                        'new_pending_submissions',
                        context['requester'],
                        preprint,
                        timestamp,
                        abstract_provider=preprint.provider,
                        **context)
