import logging

from osf.models import NotificationType, NotificationTypeEnum, OSFUser, UserActivityCounter, Email
from osf.models.spam import SpamStatus
from django.db import transaction
from django.db.models import OuterRef, Subquery, Case, When, CharField, Count, Q
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
FILTER_PRESETS = {
    'all': {},
    'active': {'is_active': True},
    'internal': {'is_active': True, 'is_staff': True, 'username__endswith': '@cos.io'},
}

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


def build_query(node):
    """
    Convert a filter tree into a Django Q object.
    """

    if 'field' in node:
        value = node['value']
        lookup = node['lookup']
        negated_lookups = {  # not native Django field lookups
            'not_contains': 'contains',
            'not_icontains': 'icontains',
        }

        if lookup == 'in':
            value = [v.strip() for v in value.split(',')]

        if lookup in negated_lookups:
            return ~Q(**{
                f'{node["field"]}__{negated_lookups[lookup]}': value
            })

        return Q(**{
            f'{node["field"]}__{lookup}': value
        })

    operator = node.get('operator', 'AND')
    children = node.get('children', [])

    if not children:
        return Q()

    query = build_query(children[0])

    for child in children[1:]:
        if operator == 'AND':
            query &= build_query(child)
        else:
            query |= build_query(child)

    return query

def create_campaign_recipients(filters, campaign_id):
    qs = (
        OSFUser.objects
        .filter(filters)
        .annotate(activity_score=Coalesce(Subquery(counter_subquery), 0))
        .values_list(
            'id',
            'activity_score',
        )
    )

    for rows in batched(qs.iterator(chunk_size=BULK_CREATE_SIZE), BULK_CREATE_SIZE):
        NotificationCampaignRecipient.objects.bulk_create(
            [
                NotificationCampaignRecipient(
                    campaign_id=campaign_id,
                    user_id=user_id,
                    activity_score=activity_score,
                )
                for user_id, activity_score in rows
            ],
            ignore_conflicts=True
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

    # Minimum and maximum activity are mutually exclusive and use the same threshold.
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


def get_campaign_recipient_stats(campaign_id):
    return NotificationCampaignRecipient.objects.filter(
        campaign_id=campaign_id
    ).aggregate(
        recipient_count=Count('id'),
        sent_count=Count(
            'id',
            filter=Q(status=NotificationCampaignRecipientStatus.SENT),
        ),
        failed_count=Count(
            'id',
            filter=Q(
                status__in=[
                    NotificationCampaignRecipientStatus.FAILED,
                    NotificationCampaignRecipientStatus.SKIPPED,
                ]
            ),
        ),
    )

@celery_app.task(name='email.process_campaign_retry')
def process_campaign_retry(*args, **kwargs):
    campaign_id = kwargs.get('campaign_id')
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if kwargs.get('run_id') != campaign.run_id:
        return

    final_status = NotificationCampaignStatus.COMPLETED

    if campaign.status != NotificationCampaignStatus.CANCELLED:
        failed_recipients = NotificationCampaignRecipient.objects.filter(campaign=campaign, status=NotificationCampaignRecipientStatus.FAILED)
        max_retries = campaign.metadata.get('execution', {}).get('max_retries', settings.DEFAULT_CAMPAIGN_MAX_RETRIES)
        batch_size = campaign.metadata.get('execution', {}).get('batch_size', settings.DEFAULT_CAMPAIGN_BATCH_SIZE)
        failed_recipients_count = failed_recipients.count()
        if failed_recipients_count:
            if campaign.retries < max_retries:
                message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                           f'Retrying {failed_recipients_count} failed recipients, '
                           f'previous retry attempts: {campaign.retries}/{max_retries}')
                logger.info(message)
                sentry.log_message(message)
                campaign.retries += 1
                campaign.save(update_fields=['retries'])
                retry_group = build_campaign_group(
                    batch_size=batch_size,
                    campaign_id=campaign_id,
                    restart_failed=True,
                    notification_type_name=campaign.notification_type.name,
                    context=campaign.metadata.get('context', {}),
                    run_id=campaign.run_id,
                )
                chain(
                    retry_group,
                    process_campaign_retry.si(campaign_id=campaign_id, run_id=campaign.run_id),
                ).apply_async()
                return

            final_status = NotificationCampaignStatus.PARTIALLY_COMPLETED
    else:
        message = f'[Notification Campaign #{campaign_id}] WARNING: Campaign {campaign.name} was cancelled.'
        logger.info(message)
        sentry.log_message(message)

    # Refresh in case the campaign was cancelled while we were running.
    campaign.refresh_from_db(fields=['status', 'completed_at'])

    # Sync statistics regardless of status.
    stats = get_campaign_recipient_stats(campaign_id)
    campaign.recipient_count = stats['recipient_count']
    campaign.sent_count = stats['sent_count']
    campaign.failed_count = stats['failed_count']

    if campaign.completed_at is None:
        campaign.completed_at = timezone.now()

    # Don't overwrite CANCELLED.
    if campaign.status != NotificationCampaignStatus.CANCELLED:
        campaign.status = final_status

    campaign.save()


@celery_app.task(name='email.start_notification_campaign')
def start_notification_campaign(campaign_id, restart_failed=False, restart_stuck=False):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    filters = campaign.metadata.get('filters', {})
    context = campaign.metadata.get('context', {})
    notification_type_name = campaign.notification_type.name

    if hasattr(NotificationTypeEnum, notification_type_name):
        del getattr(NotificationTypeEnum, notification_type_name).instance

    if predefined_filter_name := filters.get('predefined'):
        filters = Q(**FILTER_PRESETS.get(predefined_filter_name, {}))
    else:
        filters = build_query(filters.get('manual', []))

    if not restart_failed and not restart_stuck:
        recipients_creation_started_at = timezone.now()
        create_campaign_recipients(filters=filters, campaign_id=campaign_id)
        campaign.recipient_count = NotificationCampaignRecipient.objects.filter(campaign_id=campaign_id).count()
        campaign.save()
        recipients_creation_finished_at = timezone.now()
        recipients_creation_run_time = (recipients_creation_finished_at - recipients_creation_started_at).total_seconds()
        message = (f'[Notification Campaign #{campaign_id}] INFO: '
                   f'Recipients creation finished in {recipients_creation_run_time} seconds '
                   f'(start={recipients_creation_started_at}, finish={recipients_creation_finished_at}) '
                   f'for Campaign {campaign.name} (start={campaign.started_at}).')
        logger.info(message)
        sentry.log_message(message)

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
        developer_reminder=True,
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

    chain(*workflow, process_campaign_retry.si(campaign_id=campaign_id, run_id=campaign.run_id)).apply_async()


@celery_app.task(name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(
    context,
    recipients_ids,
    notification_type_name='blank',
    campaign_id=None,
    run_id=None,
    developer_reminder=False,
):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if campaign.run_id != run_id:
        return
    if campaign.status == NotificationCampaignStatus.CANCELLED:
        logger.warning(f"Campaign {campaign_id} was cancelled")
        return
    batch_started_at = timezone.now()
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
            message = f'[Notification Campaign #{campaign_id}] ERROR: Batch failed due to none notification_type (template)'
            logger.error(message)
            sentry.log_message(message)
            return

    if developer_reminder:
        execution_time_window = campaign.metadata.get('execution', {}).get('time_window', settings.DEFAULT_CAMPAIGN_WINDOW_TIME)
        if campaign.started_at < timezone.now() - timedelta(seconds=execution_time_window):
            # Atomic claim so concurrent high-activity batches only alert once
            updated = NotificationCampaign.objects.filter(
                pk=campaign_id,
                developer_reminder_sent=False,
            ).update(developer_reminder_sent=True)
            if updated:
                message = (
                    f'[Notification Campaign #{campaign_id}] WARNING: Campaign {campaign.name} exceeded '
                    f'its high-activity execution time window ({execution_time_window} seconds).'
                )
                logger.warning(message)
                sentry.log_message(message)

    recipients_qs = NotificationCampaignRecipient.objects.filter(id__in=recipients_ids).select_related('user')
    recipient_records = []
    recipients_qs_annotated = recipients_qs.annotate(
        recipient_address=Case(
            When(user__username__contains='@', then='user__username'),
            default=Subquery(first_email_subquery),
            output_field=CharField(),
        )
    )
    valid_emails_qs = recipients_qs_annotated.exclude(recipient_address__isnull=True)
    invalid_emails_qs = recipients_qs_annotated.filter(recipient_address__isnull=True)
    invalid_emails_qs.update(status=NotificationCampaignRecipientStatus.SKIPPED, error_message='Invalid email address')

    if campaign.metadata.get('sendgrid_bulk', False):
        # NOTE: sendgrid bulk send feature has not been fully implemented and tested
        recipient_emails = list(valid_emails_qs.values_list('recipient_address', flat=True))
        try:
            send_email_with_send_grid(to_addr=recipient_emails, notification_type=notification_type, context=context)
            valid_emails_qs.update(status=NotificationCampaignRecipientStatus.SENT, error_message=None)
        except Exception as exc:
            message = (f'[Notification Campaign #{campaign_id}] ERROR: '
                       f'Campaign {campaign.name} sendgrid bulk request failed, error={str(exc)}')
            logger.error(message)
            sentry.log_message(message)
            valid_emails_qs.update(status=NotificationCampaignRecipientStatus.FAILED, error_message=str(exc))
    else:
        for recipient in valid_emails_qs:
            notification_started_at = timezone.now()
            try:
                notification_type.emit(
                    user=recipient.user,
                    event_context=context,
                    save=False,  # Too many write operations
                )
                recipient.status = NotificationCampaignRecipientStatus.SENT
                recipient.error_message = None
                recipient_records.append(recipient)
            except Exception as exc:
                message = (f'[Notification Campaign #{campaign_id}] ERROR:'
                           f'SendGrid request failed for user {recipient.user.username} ({recipient.user._id}),'
                           f'error={str(exc)}')
                logger.error(message)
                sentry.log_message(message)
                recipient.status = NotificationCampaignRecipientStatus.FAILED
                recipient.error_message = str(exc)
                recipient_records.append(recipient)
            notification_finished_at = timezone.now()
            notification_sent_run_time = (notification_finished_at - notification_started_at).total_seconds()
            if notification_sent_run_time > settings.ESTIMATED_PER_REQUEST_THRESHOLD:
                message = (f'[Notification Campaign #{campaign_id}] WARNING: Slow Notification, '
                           f'run_time(threshold)={notification_sent_run_time}({settings.ESTIMATED_PER_REQUEST_THRESHOLD}), '
                           f'user={recipient.user.username}({recipient.user._id})'
                           f'campaign_name={campaign.name}')
                logger.warning(message)
                sentry.log_message(message)
        NotificationCampaignRecipient.objects.bulk_update(recipient_records, ['status', 'error_message'])

    # Lock the campaign row so concurrent batches cannot overwrite counters with a stale aggregate snapshot
    with transaction.atomic():
        notification_campaign = NotificationCampaign.objects.select_for_update().get(pk=campaign_id)
        stats = get_campaign_recipient_stats(campaign_id)
        notification_campaign.sent_count = stats['sent_count']
        notification_campaign.failed_count = stats['failed_count']
        notification_campaign.save(update_fields=['sent_count', 'failed_count'])

    batch_finished_at = timezone.now()
    batch_run_time = (batch_finished_at - batch_started_at).total_seconds()
    if batch_run_time > settings.ESTIMATED_BATCH_RUN_TIME_THRESHOLD:
        message = (f'[Notification Campaign #{campaign_id}] WARNING: Slow Batch, '
                   f'run_time(threshold)={batch_run_time}({settings.ESTIMATED_BATCH_RUN_TIME_THRESHOLD}), '
                   f'campaign_name={campaign.name}')
        logger.warning(message)
        sentry.log_message(message)
    logger.info(f'[Notification Campaign #{campaign_id}] INFO: '
                f'Batch finished in {batch_run_time} seconds for campaign {campaign.name}')
