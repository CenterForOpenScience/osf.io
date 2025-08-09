import itertools
from calendar import monthrange
from datetime import date

from django.db import connection
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from celery.utils.log import get_task_logger
from osf.models import OSFUser, Notification, NotificationType, EmailTask, AbstractProvider, RegistrationProvider, \
    CollectionProvider
from framework.sentry import log_message
from osf.registrations.utils import get_registration_provider_submissions_url
from osf.utils.permissions import ADMIN
from website import settings

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def send_user_email_task(self, user_id, notification_ids, message_freq):
    try:
        user = OSFUser.objects.get(
            guids___id=user_id,
            deleted__isnull=True
        )
    except OSFUser.DoesNotExist:
        logger.error(f'OSFUser with id {user_id} does not exist')
        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, status='NO_USER_FOUND')
        email_task.error_message = 'User not found or disabled'
        email_task.save()
        return

    try:
        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, user=user, status='STARTED')
        if user.is_disabled:
            email_task.status = 'USER_DISABLED'
            email_task.error_message = 'User not found or disabled'
            email_task.save()
            return

        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications = [n.render() for n in notifications_qs]

        if not rendered_notifications:
            email_task.status = 'SUCCESS'
            email_task.save()
            return

        event_context = {
            'notifications': rendered_notifications,
            'user_fullname': user.fullname,
            'can_change_preferences': False
        }

        notification_type = NotificationType.objects.get(name=NotificationType.Type.USER_DIGEST)
        notification_type.emit(user=user, event_context=event_context, is_digest=True)

        notifications_qs.update(sent=timezone.now())

        email_task.status = 'SUCCESS'
        email_task.save()
    except Exception as e:
        try:
            user = OSFUser.objects.get(
                guids___id=user_id,
                deleted__isnull=True
            )
        except OSFUser.DoesNotExist:
            logger.error(f'OSFUser with id {user_id} does not exist')
            email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, status='NO_USER_FOUND')
            email_task.error_message = 'User not found or disabled'
            email_task.save()
            return
        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, user=user, status='RETRY')
        email_task.status = 'RETRY'
        email_task.error_message = str(e)
        email_task.save()
        logger.exception('Retrying send_user_email_task due to exception')
        raise self.retry(exc=e)

@celery_app.task(bind=True)
def send_moderator_email_task(self, user_id, provider_id, notification_ids, message_freq):
    try:
        user = OSFUser.objects.get(
            guids___id=user_id,
            deleted__isnull=True
        )
    except OSFUser.DoesNotExist:
        logger.error(f'OSFUser with id {user_id} does not exist')
        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, status='NO_USER_FOUND')
        email_task.error_message = 'User not found or disabled'
        email_task.save()
        return

    try:
        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id, user=user, status='STARTED')
        if user.is_disabled:
            email_task.status = 'USER_DISABLED'
            email_task.error_message = 'User not found or disabled'
            email_task.save()
            return

        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications = [notification.render() for notification in notifications_qs]

        if not rendered_notifications:
            log_message(f"No notifications to send for moderator user {user._id}")
            email_task.status = 'SUCCESS'
            email_task.save()
            return

        provider = AbstractProvider.objects.get(id=provider_id)
        additional_context = {}
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
            withdrawals_url = ''
            if provider.brand:
                additional_context = {
                    'logo_url': provider.brand.hero_logo_image,
                    'top_bar_color': provider.brand.primary_color
                }
        else:
            provider_type = 'preprint'
            submissions_url = f'{settings.DOMAIN}reviews/preprints/{provider._id}'
            withdrawals_url = ''
            notification_settings_url = f'{settings.DOMAIN}reviews/{provider_type}s/{provider._id}/notifications'

        event_context = {
            'notifications': rendered_notifications,
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

        notifications_qs.update(sent=timezone.now())

        email_task.status = 'SUCCESS'
        email_task.save()

    except Exception as e:
        email_task.status = 'RETRY'
        email_task.error_message = str(e)
        email_task.save()
        logger.exception('Retrying send_moderator_email_task due to exception')
        raise self.retry(exc=e)

@celery_app.task(bind=True, name='notifications.tasks.send_users_digest_email')
def send_users_digest_email():
    today = date.today()

    frequencies = ['daily']
    if today.weekday() == 0:
        frequencies.append('weekly')
    if today.day == monthrange(today.year, today.month)[1]:
        frequencies.append('monthly')

    for freq in frequencies:
        grouped_emails = get_users_emails(freq)
        for group in grouped_emails:
            user_id = group['user_id']
            notification_ids = [msg['notification_id'] for msg in group['info']]
            send_user_email_task.delay(user_id, notification_ids, freq)

@celery_app.task(bind=True, name='notifications.tasks.send_moderators_digest_email')
def send_moderators_digest_email():
    today = date.today()

    frequencies = ['daily']
    if today.weekday() == 0:
        frequencies.append('weekly')
    if today.day == monthrange(today.year, today.month)[1]:
        frequencies.append('monthly')

    for freq in frequencies:
        grouped_emails = get_moderators_emails(freq)
        for group in grouped_emails:
            user_id = group['user_id']
            provider_id = group['provider_id']
            notification_ids = [msg['notification_id'] for msg in group['info']]
            send_moderator_email_task.delay(user_id, provider_id, notification_ids, freq)

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
