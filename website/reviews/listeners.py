
from django.utils import timezone

from website.mails import mails
from website.notifications import emails, utils
from website.reviews import signals as reviews_signals

# Handle email notifications including: update comment, accept, and reject of submission.
@reviews_signals.reviews_email.connect
def reviews_notification(self, creator, template, context, action):
    recipients = list(action.target.node.contributors)
    time_now = action.created if action is not None else timezone.now()
    node = action.target.node
    emails.notify_global_event(
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
    event_type = utils.find_subscription_type('global_reviews')
    for recipient in recipients:
        user_subscriptions = emails.get_user_subscriptions(recipient, event_type)
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
