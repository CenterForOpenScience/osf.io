import itertools
from calendar import monthrange
from datetime import date
from django.db import connection
from django.utils import timezone
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError

from framework.celery_tasks import app as celery_app
from celery.utils.log import get_task_logger

from framework.postcommit_tasks.handlers import run_postcommit
from osf.models import OSFUser, Notification, NotificationTypeEnum, EmailTask, RegistrationProvider, \
    CollectionProvider, AbstractProvider
from framework.sentry import log_message
from osf.registrations.utils import get_registration_provider_submissions_url
from osf.utils.permissions import ADMIN
from website import settings
from django.apps import apps

logger = get_task_logger(__name__)


def safe_render_notification(notifications, email_task):
    """Helper to safely render notification, updating email_task on failure."""
    rendered_notifications = []
    failed_notifications = []
    for notification in notifications:
        try:
            rendered = notification.render()
        except Exception as e:
            email_task.error_message = f'Error rendering notification {notification.id}: {str(e)} \n'
            email_task.save()
            failed_notifications.append(notification.id)
            # Mark notifications that failed to render as fake sent
            notification.mark_sent(fake_sent=True)
            log_message(f'Error rendering notification, mark as fake sent: [notification_id={notification.id}]')
            continue

        rendered_notifications.append(rendered)

    return rendered_notifications, failed_notifications


def get_user_and_email_task(task_id, user_id):
    """Helper to safely fetch user and initialize EmailTask."""
    try:
        user = OSFUser.objects.get(
            guids___id=user_id,
            deleted__isnull=True
        )
    except OSFUser.DoesNotExist:
        logger.error(f'OSFUser with id {user_id} does not exist')
        email_task, _ = EmailTask.objects.get_or_create(task_id=task_id)
        email_task.status = 'NO_USER_FOUND'
        email_task.error_message = 'User not found or disabled'
        email_task.save()
        return None, email_task

    email_task, _ = EmailTask.objects.get_or_create(task_id=task_id)
    email_task.user = user
    email_task.status = 'STARTED'

    if user.is_disabled:
        email_task.status = 'USER_DISABLED'
        email_task.error_message = 'User not found or disabled'
        email_task.save()
        return None, email_task

    return user, email_task

@celery_app.task(bind=True, max_retries=5)
def send_user_email_task(self, user_id, notification_ids, **kwargs):
    user, email_task = get_user_and_email_task(self.request.id, user_id)
    if not user:
        return

    destination_address = user.email
    validator = EmailValidator()
    try:
        validator(destination_address)
    except ValidationError:
        emails_qs = self.user.emails
        if emails_qs.exists():
            destination_address = emails_qs.first().address
        try:
            validator(destination_address)
        except ValidationError:
            Notification.objects.filter(id__in=notification_ids).update(sent=timezone.now())
            logger.error(f'User {user_id} has an invalid email address.')
            email_task.status = 'Failure'
            email_task.error_message = f'User {user_id} has an invalid email address.'
            email_task.save()
            return

    try:
        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications, failed_notifications = safe_render_notification(notifications_qs, email_task)
        notifications_qs = notifications_qs.exclude(id__in=failed_notifications)

        if not rendered_notifications:
            email_task.status = 'SUCCESS'
            if email_task.error_message:
                logger.error(f'Partial success for send_user_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
                email_task.status = 'PARTIAL_SUCCESS'
            email_task.save()
            return

        event_context = {
            'notifications': rendered_notifications,
        }

        NotificationTypeEnum.USER_DIGEST.instance.emit(
            user=user,
            event_context=event_context,
            save=False
        )

        notifications_qs.update(sent=timezone.now())

        email_task.status = 'SUCCESS'
        if email_task.error_message:
            logger.error(f'Partial success for send_user_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
            email_task.status = 'PARTIAL_SUCCESS'
        email_task.save()

    except Exception as e:
        retry_count = self.request.retries
        max_retries = self.max_retries

        if retry_count >= max_retries:
            email_task.status = 'FAILURE'
            email_task.error_message = email_task.error_message + f'Max retries reached: {str(e)} \n'
            email_task.save()
            logger.error(f'Max retries reached for send_moderator_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
            return

        email_task, _ = EmailTask.objects.get_or_create(task_id=self.request.id)
        email_task.user = user
        email_task.status = 'RETRY'
        email_task.error_message = f'{str(e)} \n'
        email_task.error_message = email_task.error_message + f'Retry {retry_count}: {str(e)} \n'
        email_task.save()
        raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=5)
def send_moderator_email_task(self, user_id, notification_ids, provider_content_type_id, provider_id, **kwargs):
    user, email_task = get_user_and_email_task(self.request.id, user_id)
    if not user:
        return

    destination_address = user.email
    validator = EmailValidator()
    try:
        validator(destination_address)
    except ValidationError:
        emails_qs = user.emails
        if emails_qs.exists():
            destination_address = emails_qs.first().address
        try:
            validator(destination_address)
        except ValidationError:
            Notification.objects.filter(id__in=notification_ids).update(sent=timezone.now())
            logger.error(f'User {user_id} has an invalid email address.')
            email_task.status = 'Failure'
            email_task.error_message = f'User {user_id} has an invalid email address.'
            email_task.save()
            return

    try:
        notifications_qs = Notification.objects.filter(id__in=notification_ids)
        rendered_notifications, failed_notifications = safe_render_notification(notifications_qs, email_task)
        notifications_qs = notifications_qs.exclude(id__in=failed_notifications)

        if not rendered_notifications:
            email_task.status = 'SUCCESS'
            if email_task.error_message:
                logger.error(f'Partial success for send_moderator_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
                email_task.status = 'PARTIAL_SUCCESS'
            email_task.save()
            return

        try:
            provider = AbstractProvider.objects.get(id=provider_id)
        except AbstractProvider.DoesNotExist:
            log_message(f'Provider with id {provider_id} does not exist for model {provider.type}')
            email_task.status = 'FAILURE'
            email_task.error_message = f'Provider with id {provider_id} does not exist for model {provider.type}'
            email_task.save()
            return
        except AttributeError as err:
            log_message(f'Error retrieving provider with id {provider_id} for model {provider.type}: {err}')
            email_task.status = 'FAILURE'
            email_task.error_message = f'Error retrieving provider with id {provider_id} for model {provider.type}: {err}'
            email_task.save()
            return

        if provider is None:
            log_message(f'Provider with id {provider_id} does not exist for model {provider.type}')
            email_task.status = 'FAILURE'
            email_task.error_message = f'Provider with id {provider_id} does not exist for model {provider.type}'
            email_task.save()
            return

        current_moderators = provider.get_group('moderator')
        if current_moderators is None or not current_moderators.user_set.filter(id=user.id).exists():
            current_admins = provider.get_group('admin')
            if current_admins is None or not current_admins.user_set.filter(id=user.id).exists():
                log_message(f"User is not a moderator for provider {provider._id} - notifications will be marked as sent.")
                email_task.status = 'AUTO_FIXED'
                email_task.error_message = f'User is not a moderator for provider {provider._id}'
                email_task.save()
                notifications_qs.update(sent=timezone.now(), fake_sent=True)
                return

        additional_context = {}
        logo = None
        if isinstance(provider, RegistrationProvider):
            provider_type = 'registration'
            base_submissions_url = get_registration_provider_submissions_url(provider)
            submissions_url = f'{base_submissions_url}?status=pending'
            withdrawals_url = f'{base_submissions_url}?status=pending_withdraw'
            notification_settings_url = f'{settings.DOMAIN}registries/{provider._id}/moderation/notifications'
            if provider.brand:
                additional_context = {
                    'logo_url': provider.brand.hero_logo_image,
                    'top_bar_color': provider.brand.primary_color
                }
            else:
                logo = settings.OSF_REGISTRIES_LOGO
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
                logo = settings.OSF_REGISTRIES_LOGO
        else:
            provider_type = 'preprint'
            submissions_url = f'{settings.DOMAIN}preprints/{provider._id}/moderation/submissions'
            withdrawals_url = f'{settings.DOMAIN}preprints/{provider._id}/moderation/withdrawals?status=pending'
            notification_settings_url = f'{settings.DOMAIN}preprints/{provider._id}/moderation/notifications'
            logo = provider._id if not provider.is_default else settings.OSF_PREPRINTS_LOGO

        event_context = {
            'notifications': rendered_notifications,
            'user_fullname': user.fullname,
            'notification_settings_url': notification_settings_url,
            'reviews_withdrawal_url': withdrawals_url,
            'reviews_submissions_url': submissions_url,
            'provider_type': provider_type,
            'is_admin': provider.get_group(ADMIN).user_set.filter(id=user.id).exists(),
            'logo': logo,
            **additional_context,
        }

        NotificationTypeEnum.DIGEST_REVIEWS_MODERATORS.instance.emit(
            user=user,
            subscribed_object=user,
            event_context=event_context,
            save=False
        )

        notifications_qs.update(sent=timezone.now())

        email_task.status = 'SUCCESS'
        if email_task.error_message:
            logger.error(f'Partial success for send_moderator_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
            email_task.status = 'PARTIAL_SUCCESS'
        email_task.save()

    except Exception as e:
        retry_count = self.request.retries
        max_retries = self.max_retries

        if retry_count >= max_retries:
            email_task.status = 'FAILURE'
            email_task.error_message = email_task.error_message + f'\nMax retries reached: {str(e)}'
            email_task.save()
            logger.error(f'Max retries reached for send_moderator_email_task for user {user_id}. Task id: {self.request.id}. Errors: {email_task.error_message}')
            return

        email_task.status = 'RETRY'
        email_task.error_message = email_task.error_message + f'Retry {retry_count}: {str(e)} \n'
        email_task.save()
        raise self.retry(exc=e)

@celery_app.task(name='notifications.tasks.send_users_digest_email')
def send_users_digest_email(dry_run=False):
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
            if not dry_run:
                send_user_email_task.delay(user_id, notification_ids)

@celery_app.task(name='notifications.tasks.send_moderators_digest_email')
def send_moderators_digest_email(dry_run=False):
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
            provider_content_type_id = group['provider_content_type_id']
            notification_ids = [msg['notification_id'] for msg in group['info']]
            if not dry_run:
                send_moderator_email_task.delay(user_id, notification_ids, provider_content_type_id, provider_id)

def get_moderators_emails(message_freq: str):
    """Get all emails for reviews moderators that need to be sent, grouped by users AND providers.
    :param send_type: from NOTIFICATION_TYPES, could be "email_digest" or "email_transactional"
    :return Iterable of dicts of the form:
    """
    sql = """
        SELECT
            json_build_object(
                'user_id', osf_guid._id,
                'provider_id', ns.object_id,
                'provider_content_type_id', ns.content_type_id,
                'info', json_agg(
                    json_build_object(
                        'notification_id', n.id
                    )
                )
            )
        FROM osf_notification AS n
        INNER JOIN osf_notificationsubscription_v2 AS ns ON n.subscription_id = ns.id
        INNER JOIN osf_notificationtype AS nt ON ns.notification_type_id = nt.id
        LEFT JOIN osf_guid ON ns.user_id = osf_guid.object_id
        WHERE n.sent IS NULL
            AND ns.message_frequency = %s
            AND nt.name IN (%s, %s)
            AND nt.name NOT IN (%s, %s, %s)
            AND osf_guid.content_type_id = (
                SELECT id FROM django_content_type WHERE model = 'osfuser'
            )
        GROUP BY osf_guid._id, ns.object_id, ns.content_type_id
        ORDER BY osf_guid._id ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql,
            [
                message_freq,
                NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                NotificationTypeEnum.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
                NotificationTypeEnum.DIGEST_REVIEWS_MODERATORS.value,
                NotificationTypeEnum.USER_DIGEST.value,
                NotificationTypeEnum.USER_NO_ADDON.value,
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
        INNER JOIN osf_notificationsubscription_v2 AS ns ON n.subscription_id = ns.id
        INNER JOIN osf_notificationtype AS nt ON ns.notification_type_id = nt.id
        LEFT JOIN osf_guid ON ns.user_id = osf_guid.object_id
        WHERE n.sent IS NULL
            AND ns.message_frequency = %s
            AND nt.name NOT IN (%s, %s, %s, %s, %s)
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
                NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                NotificationTypeEnum.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
                NotificationTypeEnum.DIGEST_REVIEWS_MODERATORS.value,
                NotificationTypeEnum.USER_DIGEST.value,
                NotificationTypeEnum.USER_NO_ADDON.value,
            ]
        )
        return itertools.chain.from_iterable(cursor.fetchall())


@run_postcommit(once_per_request=False, celery=True)
@celery_app.task(max_retries=5, default_retry_delay=60)
def remove_supplemental_node_from_preprints(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')

    node = AbstractNode.load(node_id)
    node.preprints.filter(node__isnull=False).update(node=None)


@run_postcommit(once_per_request=False, celery=True)
@celery_app.task(max_retries=5, default_retry_delay=60)
def remove_subscription_task(node_id):
    from django.contrib.contenttypes.models import ContentType
    AbstractNode = apps.get_model('osf.AbstractNode')
    NotificationSubscription = apps.get_model('osf.NotificationSubscription')
    node = AbstractNode.load(node_id)
    NotificationSubscription.objects.filter(
        object_id=node.id,
        content_type=ContentType.objects.get_for_model(node),
    ).delete()


@celery_app.task(bind=True, name='notifications.tasks.send_users_instant_digest_email')
def send_users_instant_digest_email(self, dry_run=False, **kwargs):
    """Send pending "instant' digest emails.
    :return:
    """
    grouped_emails = get_users_emails('instantly')
    for group in grouped_emails:
        user_id = group['user_id']
        notification_ids = [msg['notification_id'] for msg in group['info']]
        if not dry_run:
            send_user_email_task.delay(user_id, notification_ids)

@celery_app.task(bind=True, name='notifications.tasks.send_moderators_instant_digest_email')
def send_moderators_instant_digest_email(self, dry_run=False, **kwargs):
    """Send pending "instant' digest emails.
    :return:
    """
    grouped_emails = get_moderators_emails('instantly')
    for group in grouped_emails:
        user_id = group['user_id']
        provider_id = group['provider_id']
        provider_content_type_id = group['provider_content_type_id']
        notification_ids = [msg['notification_id'] for msg in group['info']]
        if not dry_run:
            send_moderator_email_task.delay(user_id, notification_ids, provider_content_type_id, provider_id)

@celery_app.task(bind=True, name='notifications.tasks.send_no_addon_email')
def send_no_addon_email(self, dry_run=False, **kwargs):
    """Send NO_ADDON emails.
    :return:
    """
    notification_qs = Notification.objects.filter(
        sent__isnull=True,
        subscription__notification_type__name=NotificationTypeEnum.USER_NO_ADDON.value,
        created__lte=timezone.now() - settings.NO_ADDON_WAIT_TIME
    )
    for notification in notification_qs:
        user = notification.subscription.user
        if not dry_run:
            if len([addon for addon in user.get_addons() if addon.config.short_name != 'osfstorage']) == 0:
                try:
                    notification.send()
                except Exception as e:
                    logger.error(f'Error sending NO_ADDON email to user {user.id}: {str(e)}')
                    pass
            else:
                notification.mark_sent()


@celery_app.task(bind=True, name='notifications.tasks.notifications_cleanup_task')
def notifications_cleanup_task(self, dry_run=False, **kwargs):
    """Remove old notifications and email tasks from the database."""

    cutoff_date = timezone.now() - settings.NOTIFICATIONS_CLEANUP_AGE
    old_notifications = Notification.objects.filter(sent__lt=cutoff_date)
    old_email_tasks = EmailTask.objects.filter(created_at__lt=cutoff_date)

    if dry_run:
        notifications_count = old_notifications.count()
        email_tasks_count = old_email_tasks.count()
        logger.info(f'[Dry Run] Notifications Cleanup Task: {notifications_count} notifications and {email_tasks_count} email tasks would be deleted.')
        return

    deleted_notifications_count, _ = old_notifications.delete()
    deleted_email_tasks_count, _ = old_email_tasks.delete()
    logger.info(f'Notifications Cleanup Task: Deleted {deleted_notifications_count} notifications and {deleted_email_tasks_count} email tasks older than {cutoff_date}.')
