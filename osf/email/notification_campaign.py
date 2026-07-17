import logging
from enum import IntEnum

from osf.models import NotificationType, NotificationTypeEnum, OSFUser, UserActivityCounter, Email
from osf.models.spam import SpamStatus
from django.db.models import OuterRef, Subquery, Exists, F, Q, Case, When, CharField, IntegerField, Value
from django.db.models.functions import Coalesce
from framework.celery_tasks import app as celery_app
from celery import chord
from django.utils import timezone
from datetime import timedelta
from osf.models.notification_campaign import NotificationCampaign, NotificationCampaignRecipient, NotificationCampaignStatus, NotificationCampaignRecipientStatus
from osf.email import send_email_with_send_grid
from framework import sentry

logger = logging.getLogger(__name__)

ACTIVITY_ACTIVE_THRESHOLD = 5000
ACTIVITY_SPAM_THRESHOLD = 100000


class ActivityPriority(IntEnum):
    """Numeric priorities for ordering recipients (higher = send first)."""
    SPAM_NON_ACTIVE = 0
    NON_ACTIVE = 1
    SPAM_ACTIVE = 2
    ACTIVE = 3


first_email_subquery = (
    Email.objects
    .filter(user=OuterRef('pk'))
    .values('address')[:1]
)


counter_subquery = (
    UserActivityCounter.objects
    .filter(_id=OuterRef('guids___id'))
    .values('total')[:1]
)

def filter_users(filters, campaign_id=None, restart_failed=False):
    qs = OSFUser.objects.all()
    if campaign_id:
        if restart_failed:
            already_sent_subquery = NotificationCampaignRecipient.objects.filter(
                campaign_id=campaign_id,
                user_id=OuterRef('pk'),
                status__in=['sent', 'pending']
            )
        else:
            already_sent_subquery = NotificationCampaignRecipient.objects.filter(
                campaign_id=campaign_id,
                user_id=OuterRef('pk'),
            )

        qs = OSFUser.objects.annotate(already_sent=Exists(already_sent_subquery)).filter(already_sent=False)

    qs = qs.filter(**filters)

    return qs


def get_filtered_batches(filters, batch_size=1000, campaign_id=None, restart_failed=False):
    qs = filter_users(filters, campaign_id, restart_failed=restart_failed)

    is_spam = Q(spam_status=SpamStatus.SPAM)
    qs = (
        qs
        .annotate(
            activity_total=Coalesce(Subquery(counter_subquery), 0),
        ).annotate(
            activity_priority=Case(
                When(~is_spam & Q(activity_total__gte=ACTIVITY_ACTIVE_THRESHOLD), then=Value(ActivityPriority.ACTIVE)),
                When(is_spam & Q(activity_total__gte=ACTIVITY_SPAM_THRESHOLD), then=Value(ActivityPriority.SPAM_ACTIVE)),
                When(~is_spam, then=Value(ActivityPriority.NON_ACTIVE)),
                default=Value(ActivityPriority.SPAM_NON_ACTIVE),
                output_field=IntegerField(),
            ),
        ).order_by('-activity_priority', '-activity_total', '-date_registered', '-id')
    )

    last_priority = None
    last_total = None
    last_date = None
    last_id = None

    while True:
        batch_qs = qs

        if last_priority is not None:
            batch_qs = batch_qs.filter(
                Q(activity_priority__lt=last_priority) |
                Q(activity_priority=last_priority, activity_total__lt=last_total) |
                Q(activity_priority=last_priority, activity_total=last_total, date_registered__lt=last_date) |
                Q(activity_priority=last_priority, activity_total=last_total, date_registered=last_date, id__lt=last_id)
            )

        batch = batch_qs[:batch_size]
        rows = list(batch.values_list('id', 'activity_priority', 'activity_total', 'date_registered'))

        if not rows:
            break

        batch_ids = [r[0] for r in rows]
        last_id, last_priority, last_total, last_date = rows[-1]

        yield batch_ids


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
    max_retries = campaign.metadata.get('execution', {}).get('max_retries', 3)
    batch_size = campaign.metadata.get('execution', {}).get('batch_size', 1000)
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
        filters = {'id__in': failed_recipients.values_list('user_id', flat=True)}
        tasks = []
        for batch in get_filtered_batches(filters=filters, batch_size=batch_size, campaign_id=campaign_id):
            tasks.append(
                send_campaign_batch.s(
                    notification_type_name=campaign.notification_type.name,
                    recipients_ids=batch,
                    context=campaign.metadata.get('context', {}),
                    campaign_id=campaign_id,
                )
            )
        chord(tasks)(
            process_campaign_retry.s(campaign_id=campaign_id)
        )
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
    tasks = []
    total_recipients = 0
    batch_size = campaign.metadata.get('execution', {}).get('batch_size', 1000)
    for batch in get_filtered_batches(filters=filters, batch_size=batch_size, campaign_id=campaign_id, restart_failed=restart_failed):
        tasks.append(
            send_campaign_batch.s(
                notification_type_name=notification_type_name,
                recipients_ids=batch,
                context=context,
                campaign_id=campaign_id,
            )
        )
        total_recipients += len(batch)
    if not restart_failed:
        campaign.recipient_count = total_recipients
        campaign.save(update_fields=['recipient_count'])

    chord(tasks)(
        process_campaign_retry.s(campaign_id=campaign_id)
    )


@celery_app.task(name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(context, recipients_ids, notification_type_name='blank', campaign_id=None):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
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

    recipients_qs = OSFUser.objects.filter(id__in=recipients_ids)
    recipient_records = {
        'to_create': [],
        'to_update': [],
    }
    existing = {
        r.user_id: r
        for r in NotificationCampaignRecipient.objects.filter(
            campaign_id=campaign_id,
            user_id__in=recipients_ids,
        )
    }
    success_count = 0
    failure_count = 0
    if campaign.metadata.get('sendgrid_bulk', False):
        recipients_qs_annotated = recipients_qs.annotate(
            recipient_address=Case(
                When(username__contains='@', then='username'),
                default=Subquery(first_email_subquery),
                output_field=CharField(),
            )
        )
        recipient_emails = list(recipients_qs_annotated.values_list('recipient_address', flat=True))
        send_email_with_send_grid(to_addr=recipient_emails, notification_type=notification_type, context=context)
        success_count = len(recipient_emails)
    else:
        for recipient in recipients_qs:
            recipient_record = existing.get(recipient.id)

            if recipient_record is None:
                recipient_record = NotificationCampaignRecipient(
                    campaign_id=campaign_id,
                    user=recipient,
                )
                operation = 'to_create'
            else:
                operation = 'to_update'

            try:
                notification_type.emit(
                    user=recipient,
                    event_context=context,
                    save=False,  # Too many write operations
                )

                recipient_record.status = NotificationCampaignRecipientStatus.SENT
                recipient_record.error_message = None
                recipient_records[operation].append(recipient_record)
                success_count += 1

            except Exception as exc:
                logger.error(exc)  # TODO update error
                sentry.log_exception(exc)  # TODO update error

                recipient_record.status = NotificationCampaignRecipientStatus.FAILED
                recipient_record.error_message = str(exc)
                recipient_records[operation].append(recipient_record)

                failure_count += 1
                pass

    NotificationCampaignRecipient.objects.bulk_create(recipient_records['to_create'])
    NotificationCampaignRecipient.objects.bulk_update(recipient_records['to_update'], ['status', 'error_message'])

    NotificationCampaign.objects.filter(pk=campaign_id).update(sent_count=F('sent_count') + success_count, failed_count=F('failed_count') + failure_count)
    logger.info('Batch finished')  # TODO: add/update logs
