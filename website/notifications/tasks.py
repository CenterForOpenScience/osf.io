"""
Tasks for making even transactional emails consolidated.
"""
import itertools
from datetime import datetime
from calendar import monthrange

from django.db import connection

from framework.celery_tasks import app as celery_app
from framework.sentry import log_message
from osf.models import (
    OSFUser,
    AbstractProvider,
    RegistrationProvider,
    CollectionProvider,
    Notification,
    NotificationType,
)
from osf.registrations.utils import get_registration_provider_submissions_url
from osf.utils.permissions import ADMIN
from website import settings


@celery_app.task(name='website.notifications.tasks.send_users_digest_email', max_retries=0)
def send_users_digest_email():
    """Send pending emails.
    """
    today = datetime.today().date()

    # Run for yesterday
    _send_user_digest('daily')

    # Run only on Mondays
    if today.weekday() == 0:  # Monday is 0
        _send_user_digest('weekly')

    # Run only on the last day of the month
    last_day = monthrange(today.year, today.month)[1]
    if today.day == last_day:
        _send_user_digest('monthly')


@celery_app.task(name='website.notifications.tasks.send_moderators_digest_email', max_retries=0)
def send_moderators_digest_email():
    """Send pending emails.
    """
    today = datetime.today().date()

    # Run for yesterday
    _send_moderator_digest('daily')

    # Run only on Mondays
    if today.weekday() == 0:  # Monday is 0
        _send_moderator_digest('weekly')

    # Run only on the last day of the month
    last_day = monthrange(today.year, today.month)[1]
    if today.day == last_day:
        _send_moderator_digest('monthly')


def _send_user_digest(message_freq):
    """
    Called by `send_users_email`. Send all global and node-related notification emails.
    """
    grouped_emails = get_users_emails(message_freq)
    for group in grouped_emails:
        user = OSFUser.load(group['user_id'])
        if not user:
            log_message(f"User with id={group['user_id']} not found")
            continue
        if user.is_disabled:
            continue

        info = group['info']
        notification_ids = [message['notification_id'] for message in info]
        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications = [notification.render() for notification in notifications_qs]

        if not rendered_notifications:
            log_message(f"No notifications to send for user {user._id} with message frequency {message_freq}")
            continue
        event_context = {
            'notifications': ' <br>'.join(rendered_notifications),
            'user_fullname': user.fullname,
            'can_change_preferences': False
        }

        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
        notification_type.emit(user=user, event_context=event_context, is_digest=True)

        for notification in notifications_qs:
            notification.mark_sent()

def _send_moderator_digest(message_freq):
    """
    Called by `send_users_email`. Send all reviews triggered emails.
    """
    grouped_emails = get_moderators_emails(message_freq)
    for group in grouped_emails:
        user = OSFUser.load(group['user_id'])
        if not user:
            log_message(f"User with id={group['user_id']} not found")
            continue
        if user.is_disabled:
            continue

        info = group['info']
        notification_ids = [message['notification_id'] for message in info]
        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications = [notification.render() for notification in notifications_qs]

        provider = AbstractProvider.objects.get(id=group['provider_id'])
        additional_context = dict()
        if isinstance(provider, RegistrationProvider):
            provider_type = 'registration'
            submissions_url = get_registration_provider_submissions_url(provider)
            withdrawals_url = f'{submissions_url}?state=pending_withdraw'
            notification_settings_url = f'{settings.DOMAIN}registries/{provider._id}/moderation/notifications'
            if provider.brand:
                additional_context = {
                    'logo_url': provider.brand.hero_logo_image,
                    'top_bar_color': provider.brand.primary_color
                }
        elif isinstance(provider, CollectionProvider):
            provider_type = 'collection'
            submissions_url = f'{settings.DOMAIN}collections/{provider._id}/moderation/'
            notification_settings_url = f'{settings.DOMAIN}registries/{provider._id}/moderation/notifications'
            if provider.brand:
                additional_context = {
                    'logo_url': provider.brand.hero_logo_image,
                    'top_bar_color': provider.brand.primary_color
                }
            withdrawals_url = ''
        else:
            provider_type = 'preprint'
            submissions_url = f'{settings.DOMAIN}reviews/preprints/{provider._id}',
            withdrawals_url = ''
            notification_settings_url = f'{settings.DOMAIN}reviews/{provider_type}s/{provider._id}/notifications'

        if not rendered_notifications:
            log_message(f"No notifications to send for user {user._id} with message frequency {message_freq}")
            continue
        event_context = {
            'notifications': ' <br>'.join(rendered_notifications),
            'user_fullname': user.fullname,
            'can_change_preferences': False,
            'notification_settings_url': notification_settings_url,
            'withdrawals_url': withdrawals_url,
            'submissions_url': submissions_url,
            'provider_type': provider_type,
            'additional_context': additional_context,
            'is_admin': provider.get_group(ADMIN).user_set.filter(id=user.id).exists()
        }

        notification_type = NotificationType.objects.get(name=NotificationType.Type.DIGEST_REVIEWS_MODERATORS)
        notification_type.emit(user=user, event_context=event_context, is_digest=True)

        for notification in notifications_qs:
            notification.mark_sent()


def get_moderators_emails(message_freq: str):
    """Get all emails for reviews moderators that need to be sent, grouped by users AND providers.
    :param send_type: from NOTIFICATION_TYPES, could be "email_digest" or "email_transactional"
    :return Iterable of dicts of the form:
    """
    sql = """
        SELECT
            json_build_object(
                'user_id', osf_guid._id,
                'provider_id', (n.event_context ->> 'provider_id'),
                'info', json_agg(
                    json_build_object(
                        'notification_id', n.id
                    )
                )
            )
        FROM osf_notification AS n
        INNER JOIN osf_notificationsubscription AS ns ON n.subscription_id = ns.id
        INNER JOIN osf_notificationtype AS nt ON ns.notification_type_id = nt.id
        LEFT JOIN osf_guid ON ns.user_id = osf_guid.object_id
        WHERE n.sent IS NULL
            AND ns.message_frequency = %s
            AND nt.name IN (%s, %s)
            AND osf_guid.content_type_id = (
                SELECT id FROM django_content_type WHERE model = 'osfuser'
            )
        GROUP BY osf_guid._id, (n.event_context ->> 'provider_id')
        ORDER BY osf_guid._id ASC
        """

    with connection.cursor() as cursor:
        cursor.execute(sql,
            [
                message_freq,
                NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value
            ]
        )
        return itertools.chain.from_iterable(cursor.fetchall())

def get_users_emails(message_freq):
    """Get all emails that need to be sent.
    NOTE: These do not include reviews triggered emails for moderators.
    """

    sql = """
        SELECT
            json_build_object(
                'user_id', osf_guid._id,
                'info', json_agg(
                    json_build_object(
                        'notification_id', n.id
                    )
                )
            )
        FROM osf_notification AS n
        INNER JOIN osf_notificationsubscription AS ns ON n.subscription_id = ns.id
        INNER JOIN osf_notificationtype AS nt ON ns.notification_type_id = nt.id
        LEFT JOIN osf_guid ON ns.user_id = osf_guid.object_id
        WHERE n.sent IS NULL
            AND ns.message_frequency = %s
            AND nt.name NOT IN (%s, %s)
            AND osf_guid.content_type_id = (
                SELECT id FROM django_content_type WHERE model = 'osfuser'
            )
        GROUP BY osf_guid._id
        ORDER BY osf_guid._id ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql,
            [
                message_freq,
                NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value
            ]
        )
        return itertools.chain.from_iterable(cursor.fetchall())
