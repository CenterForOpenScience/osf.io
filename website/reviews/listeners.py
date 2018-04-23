
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
    from osf.models import NotificationSubscription
    from website import settings
    provider_subscription = NotificationSubscription.load('{}_new_pending_submissions'.format(context['reviewable'].provider._id))
    from api.preprint_providers.permissions import GroupHelper
    for subscriber in provider_subscription.email_transactional.all():
        context['is_admin'] = GroupHelper(context['reviewable'].provider).get_group('admin').user_set.filter(id=subscriber.id).exists()
        mails.send_mail(
            subscriber.username,
            mails.REVIEWS_SUBMISSION_NOTIFICATION_MODERATORS,
            mimetype='html',
            user=subscriber,
            **context
        )

    for subscriber in provider_subscription.email_digest.all():
        pass
