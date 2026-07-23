import logging

from osf.models import NotificationType, NotificationTypeEnum, OSFUser, UserActivityCounter, Email
from osf.models.spam import SpamStatus
from django.db.models import OuterRef, Subquery, F, Case, When, CharField
from django.db.models.functions import Coalesce
from framework.celery_tasks import app as celery_app
from celery import group, chain
from django.utils import timezone
from datetime import timedelta
from osf.models.notification_campaign import NotificationCampaign, NotificationCampaignRecipient, NotificationCampaignStatus, NotificationCampaignRecipientStatus
from osf.email import send_email_with_send_grid
from framework import sentry
from website import settings
from itertools import batched

logger = logging.getLogger(__name__)

BULK_CREATE_SIZE = 5000

first_email_subquery = (
    Email.objects
    .filter(user=OuterRef('user_id'))
    .values('address')[:1]
)


counter_subquery = (
    UserActivityCounter.objects
    .filter(_id=OuterRef('guids___id'))
    .values('total')[:1]
)

def create_campaign_recipients(filters, campaign_id):
    qs = (
        OSFUser.objects
        .filter(**filters)
        .annotate(activity_score=Coalesce(Subquery(counter_subquery), 0))
        .values_list(
            'id',
            'activity_score',
        )
    )

    for rows in batched(qs.iterator(chunk_size=BULK_CREATE_SIZE), BULK_CREATE_SIZE):
        NotificationCampaignRecipient.objects.bulk_create(
            NotificationCampaignRecipient(
                campaign_id=campaign_id,
                user_id=user_id,
                activity_score=activity_score,
            )
            for user_id, activity_score in rows
        )


def get_campaign_recipient_batches(
    campaign_id,
    batch_size,
    restart_failed=False,
    min_activity=None,
    max_activity=None,
    spam=None,
):
    qs = NotificationCampaignRecipient.objects.filter(
        campaign_id=campaign_id,
    )

    if restart_failed:
        qs = qs.filter(status=NotificationCampaignRecipientStatus.FAILED)
    else:
        qs = qs.filter(status=NotificationCampaignRecipientStatus.PENDING)

    if min_activity is not None:
        qs = qs.filter(activity_score__gte=min_activity)

    if max_activity is not None:
        qs = qs.filter(activity_score__lt=max_activity)

    if spam is True:
        qs = qs.filter(user__spam_status=SpamStatus.SPAM)
    elif spam is False:
        qs = qs.exclude(user__spam_status=SpamStatus.SPAM)

    yield from batched(
        qs.values_list('id', flat=True).iterator(chunk_size=batch_size),
        batch_size,
    )

def build_campaign_group(
    campaign_id,
    batch_size,
    restart_failed=False,
    min_activity=None,
    max_activity=None,
    spam=None,
    **send_kwargs,
):
    tasks = []

    for batch in get_campaign_recipient_batches(
        campaign_id=campaign_id,
        batch_size=batch_size,
        restart_failed=restart_failed,
        min_activity=min_activity,
        max_activity=max_activity,
        spam=spam,
    ):
        tasks.append(
            send_campaign_batch.si(
                recipients_ids=batch,
                campaign_id=campaign_id,
                **send_kwargs,
            )
        )

    return group(tasks)


FILTER_PRESETS = {
    'all': {},
    'active': {'is_active': True},
    'internal': {'is_active': True, 'is_staff': True, 'username__endswith': '@cos.io'},
}

@celery_app.task(name='email.process_campaign_retry')
def process_campaign_retry(*args, **kwargs):
    campaign_id = kwargs.get('campaign_id')
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    failed_recipients = NotificationCampaignRecipient.objects.filter(campaign=campaign, status=NotificationCampaignRecipientStatus.FAILED)
    max_retries = campaign.metadata.get('execution', {}).get('max_retries', settings.DEFAULT_CAMPAIGN_MAX_RETRIES)
    batch_size = campaign.metadata.get('execution', {}).get('batch_size', settings.DEFAULT_CAMPAIGN_BATCH_SIZE)
    failed_recipients_count = failed_recipients.count()
    if not failed_recipients_count:
        campaign.status = NotificationCampaignStatus.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.failed_count = 0
        campaign.save(update_fields=['status', 'completed_at', 'failed_count'])
        return

    if campaign.retries < max_retries:
        message = f'[Notification Campaign] Retrying {failed_recipients_count} failed recipients for campaign {campaign_id}'
        logger.info(message)
        sentry.log_message(message)

        tasks = build_campaign_group(
            batch_size=batch_size,
            campaign_id=campaign_id,
            restart_failed=True,
            notification_type_name=campaign.notification_type.name,
            context=campaign.metadata.get('context', {}),
            run_id=campaign.run_id
        )

        chain(
            tasks,
            process_campaign_retry.si(campaign_id=campaign_id)
        ).apply_async()
        campaign.retries += 1
        campaign.save(update_fields=['retries'])
    else:
        campaign.failed_count = failed_recipients_count
        campaign.status = NotificationCampaignStatus.PARTIALLY_COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at', 'failed_count'])


@celery_app.task(name='email.start_notification_campaign')
def start_notification_campaign(campaign_id, restart_failed=False):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    filters = campaign.metadata.get('filters', {})
    context = campaign.metadata.get('context', {})
    notification_type_name = campaign.notification_type.name

    if hasattr(NotificationTypeEnum, notification_type_name):
        del getattr(NotificationTypeEnum, notification_type_name).instance

    if predefined_filter_name := filters.get('predefined'):
        filters = FILTER_PRESETS.get(predefined_filter_name, {})
    else:
        manual_filters = {}
        for item in filters.get('manual', []):
            if item['lookup'] != 'in':
                manual_filters[f'{item["field"]}__{item["lookup"]}'] = item['value']
            else:
                manual_filters[f'{item["field"]}__{item["lookup"]}'] = [value.strip() for value in item['value'].split(',')]
        filters = manual_filters

    if not restart_failed:
        create_campaign_recipients(filters=filters, campaign_id=campaign_id)

    execution = campaign.metadata.get('execution', {})
    batch_size = execution.get('batch_size', settings.DEFAULT_CAMPAIGN_BATCH_SIZE)
    activity_threshold = execution.get('activity_threshold', settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD)
    batch_task_kwargs = dict(
        batch_size=batch_size,
        campaign_id=campaign_id,
        restart_failed=restart_failed,
        notification_type_name=notification_type_name,
        context=context,
        run_id=campaign.run_id
    )

    workflow = []
    high_activity_tasks = build_campaign_group(
        min_activity=activity_threshold,
        spam=False,
        **batch_task_kwargs
    )
    if high_activity_tasks:
        workflow.append(high_activity_tasks)

    low_activity_tasks = build_campaign_group(
        max_activity=activity_threshold,
        spam=False,
        **batch_task_kwargs
    )
    if low_activity_tasks:
        workflow.append(low_activity_tasks)

    spam_users_tasks = build_campaign_group(
        spam=True,
        **batch_task_kwargs
    )
    if spam_users_tasks:
        workflow.append(spam_users_tasks)

    chain(*workflow, process_campaign_retry.si(campaign_id=campaign_id)).apply_async()


@celery_app.task(name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(context, recipients_ids, notification_type_name='blank', campaign_id=None, run_id=None):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if campaign.run_id != run_id:
        return
    if campaign.status == NotificationCampaignStatus.CANCELLED:
        logger.warning(f"Campaign {campaign_id} was cancelled")
        return
    if hasattr(NotificationTypeEnum, notification_type_name):
        notification_type = getattr(NotificationTypeEnum, notification_type_name).instance
    else:
        notification_type = NotificationType.objects.filter(
            name=notification_type_name
        ).first()  # TODO cache

        if notification_type is None:
            if campaign.status != NotificationCampaignStatus.FAILED:
                campaign.status = NotificationCampaignStatus.FAILED
                campaign.save()
            return

    execution_time_window = campaign.metadata.get('execution', {}).get('time_window', 8)
    if campaign.started_at < timezone.now() - timedelta(hours=execution_time_window):
        if not campaign.developer_reminder_sent:
            message = f'[Notification Campaign] Campaign {campaign_id} exceeded its execution time window ({execution_time_window}h).'
            logger.warning(message)
            sentry.log_message(message)
            campaign.developer_reminder_sent = True
            campaign.save()

    recipients_qs = NotificationCampaignRecipient.objects.filter(id__in=recipients_ids).select_related('user')
    recipient_records = []
    success_count = 0
    failure_count = 0
    if campaign.metadata.get('sendgrid_bulk', False):
        recipients_qs_annotated = recipients_qs.annotate(
            recipient_address=Case(
                When(user__username__contains='@', then='user_id'),
                default=Subquery(first_email_subquery),
                output_field=CharField(),
            )
        )
        valid_emails_qs = recipients_qs_annotated.exclude(recipient_address__isnull=True)
        invalid_emails_qs = recipients_qs_annotated.filter(recipient_address__isnull=True)
        recipient_emails = list(valid_emails_qs.values_list('recipient_address', flat=True))
        success_count = len(recipient_emails)
        try:
            send_email_with_send_grid(to_addr=recipient_emails, notification_type=notification_type, context=context)
        except Exception as exc:
            logger.error(exc)  # TODO update error
            sentry.log_exception(exc)  # TODO update error

            valid_emails_qs.update(status=NotificationCampaignRecipientStatus.FAILED, error_message=str(exc))
            failure_count += success_count
            success_count = 0
            pass
        invalid_emails_qs.update(status=NotificationCampaignRecipientStatus.SKIPPED, error_message='Invalid email address')

    else:
        for recipient in recipients_qs:
            try:
                notification_type.emit(
                    user=recipient.user,
                    event_context=context,
                    save=False,  # Too many write operations
                )

                recipient.status = NotificationCampaignRecipientStatus.SENT
                recipient.error_message = None
                recipient_records.append(recipient)
                success_count += 1

            except Exception as exc:
                logger.error(exc)  # TODO update error
                sentry.log_exception(exc)  # TODO update error

                recipient.status = NotificationCampaignRecipientStatus.FAILED
                recipient.error_message = str(exc)
                recipient_records.append(recipient)

                failure_count += 1
                pass

    NotificationCampaignRecipient.objects.bulk_update(recipient_records, ['status', 'error_message'])

    NotificationCampaign.objects.filter(pk=campaign_id).update(sent_count=F('sent_count') + success_count, failed_count=F('failed_count') + failure_count)
    logger.info('Batch finished')  # TODO: add/update logs
