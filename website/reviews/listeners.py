
from django.utils import timezone

from website.mails import mails
from website.notifications import utils
from website.reviews import signals as reviews_signals

# Handle email notifications including: update comment, accept, and reject of submission.
@reviews_signals.reviews_email.connect
def reviews_notification(self, creator, template, context, action):
    # Avoid AppRegistryNotReady error
    from website.notifications.emails import notify_global_event
    recipients = list(action.target.node.contributors)
    time_now = action.created if action is not None else timezone.now()
    node = action.target.node
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
    for recipient in recipients:
        user_subscriptions = get_user_subscriptions(recipient, event_type)
        context['no_future_emails'] = user_subscriptions['none']
        context['is_creator'] = recipient == context['reviewable'].node.creator
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
def reviews_submit_notification_moderators(self, context):
    # imports moved here to avoid AppRegistryNotReady error
    from osf.models import NotificationSubscription
    from website.profile.utils import get_profile_image_url
    from website.notifications import emails
    from website import settings

    # Get NotificationSubscription instance, which contains reference to all subscribers
    provider_subscription = NotificationSubscription.load('{}_new_pending_submissions'.format(context['reviewable'].provider._id))
    # Set message
    context['message'] = u'submitted {}.'.format(context['reviewable'].node.title)
    # Set url for profile image
    context['profile_image_url'] = get_profile_image_url(context['referrer'])
    # Set submission url
    context['reviews_submission_url'] = '{}reviews/preprints/{}/{}'.format(settings.DOMAIN, context['reviewable'].provider._id, context['reviewable']._id )
    # Store emails to be sent to subscribers instantly (at a 5 min interval)
    emails.store_emails(provider_subscription.email_transactional.all().values_list('guids___id', flat=True),
                        'email_transactional',
                        'new_pending_submissions',
                        context['referrer'],
                        context['reviewable'].node,
                        timezone.now(),
                        context['reviewable'].provider,
                        **context)

    # Store emails to be sent to subscribers daily
    emails.store_emails(provider_subscription.email_transactional.all().values_list('guids___id', flat=True),
                        'email_digest',
                        'new_pending_submissions',
                        context['referrer'],
                        context['reviewable'].node,
                        timezone.now(),
                        context['reviewable'].provider,
                        **context)
