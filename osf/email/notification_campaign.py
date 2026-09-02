import logging
import uuid
from osf.models import NotificationType, NotificationTypeEnum, OSFUser, UserActivityCounter, Email
from osf.models.spam import SpamStatus
from django.db import transaction
from django.db.models import OuterRef, Subquery, Case, When, CharField, Count, Q, BooleanField
from django.db.models.functions import Coalesce
from framework.celery_tasks import app as celery_app
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

        if lookup == 'isnull':
            value = BooleanField().to_python(value)

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


def build_campaign_filter_query(filters):
    """AND together optional predefined and manual filter clauses."""
    filters = filters or {}
    query = Q()
    if predefined := filters.get('predefined'):
        query &= Q(**FILTER_PRESETS.get(predefined, {}))
    if manual := filters.get('manual'):
        query &= build_query(manual)
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
        failed_recipients_count = failed_recipients.count()
        if failed_recipients_count:
            if campaign.retries < max_retries:
                message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                           f'Retrying {failed_recipients_count} failed recipients, '
                           f'previous retry attempts: {campaign.retries}/{max_retries}')
                logger.info(message)
                sentry.log_message(message)
                campaign.retries += 1
                campaign.save(update_fields=['retries', 'updated_at'])

                dispatch_campaign.apply_async(
                    args=[campaign_id, campaign.run_id],
                    kwargs={
                        'restart_failed': True,
                    },
                )
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
    notification_type_name = campaign.notification_type.name

    if hasattr(NotificationTypeEnum, notification_type_name):
        del getattr(NotificationTypeEnum, notification_type_name).instance

    recipient_filters = build_campaign_filter_query(filters)

    if not restart_failed and not restart_stuck:
        recipients_creation_started_at = timezone.now()
        create_campaign_recipients(filters=recipient_filters, campaign_id=campaign_id)
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

    dispatch_campaign.apply_async(
        args=[campaign_id, campaign.run_id],
        kwargs={
            'restart_failed': restart_failed,
            'restart_stuck': restart_stuck,
        },
    )


def assign_batch_id_to_recipients(
    campaign_id,
    batch_size,
    restart_failed=False,
    min_activity=None,
    max_activity=None,
    spam=None,
):
    batch_id = uuid.uuid4()
    filters = Q(campaign_id=campaign_id)

    if restart_failed:
        filters &= Q(
            status=NotificationCampaignRecipientStatus.FAILED,
        )
    else:
        filters &= Q(
            status=NotificationCampaignRecipientStatus.PENDING,
            batch_id__isnull=True,
        )

    if min_activity is not None:
        filters &= Q(activity_score__gte=min_activity)
    if max_activity is not None:
        filters &= Q(activity_score__lt=max_activity)

    if spam is not None:
        filters &= Q(user__spam_status=SpamStatus.SPAM) if spam else ~Q(user__spam_status=SpamStatus.SPAM)

    recipient_ids = NotificationCampaignRecipient.objects.filter(
        filters
    ).values_list('id', flat=True)[:batch_size]

    updated = NotificationCampaignRecipient.objects.filter(id__in=recipient_ids).update(batch_id=batch_id, status=NotificationCampaignRecipientStatus.QUEUED)

    if updated == 0:
        return None

    return batch_id

@celery_app.task(bind=True, name='email.dispatch_campaign')
def dispatch_campaign(self, campaign_id, run_id, restart_failed=False, restart_stuck=False):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if campaign.run_id != run_id:
        return

    if campaign.status == NotificationCampaignStatus.CANCELLED:
        logger.warning(f"Campaign {campaign_id} was cancelled")
        return
    if campaign.status != NotificationCampaignStatus.RUNNING:
        message = f'[Notification Campaign #{campaign_id}] ERROR: Campaign {campaign.name} is not in RUNNING status.'
        logger.error(message)
        sentry.log_message(message)
        return

    queued_batches_count = NotificationCampaignRecipient.objects.filter(
        campaign=campaign,
        batch_id__isnull=False,
        status=NotificationCampaignRecipientStatus.QUEUED
    ).order_by().values('batch_id').distinct().count()

    execution = campaign.metadata.get('execution', {})
    batch_size = execution.get('batch_size', settings.DEFAULT_CAMPAIGN_BATCH_SIZE)
    activity_threshold = execution.get('activity_threshold', settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD)
    max_queued_batches = execution.get('max_queued_batches', settings.MAX_QUEUED_CAMPAIGN_BATCHES)
    notification_type_name = campaign.notification_type.name
    to_queue = max_queued_batches - queued_batches_count

    priority_groups = (
        {
            'min_activity': activity_threshold,
            'spam': False,
        },
        {
            'max_activity': activity_threshold,
            'spam': False,
        },
        {
            'spam': True,
        },
    )
    total_new_queued_batches = 0
    new_queued_batches = 0
    for priority_group in priority_groups:
        no_more_recipients = False
        for _ in range(to_queue):
            batch_id = assign_batch_id_to_recipients(
                campaign_id,
                batch_size=batch_size,
                restart_failed=restart_failed,
                **priority_group,
            )

            if batch_id is None:
                no_more_recipients = True
                break

            send_campaign_batch.delay(
                context=campaign.metadata.get('context', {}),
                batch_id=batch_id,
                campaign_id=campaign_id,
                notification_type_name=notification_type_name,
                run_id=run_id,
                developer_reminder=True if priority_group == 'high_activity' else False,
            )
            new_queued_batches += 1

        to_queue -= new_queued_batches
        total_new_queued_batches += new_queued_batches
        new_queued_batches = 0
        if to_queue <= 0:
            break

    logger.info(f'[Notification Campaign #{campaign_id}] INFO: Dispatched {total_new_queued_batches} new batches for campaign {campaign.name}.')

    if no_more_recipients:
        process_campaign_retry.delay(
            campaign_id=campaign_id, run_id=campaign.run_id
        )
    else:
        self.apply_async(
            args=[campaign_id, run_id],
            kwargs={
                'restart_failed': restart_failed,
                'restart_stuck': restart_stuck,
            },
            countdown=execution.get('dispatch_interval', settings.CAMPAIGN_DISPATCH_INTERVAL),
        )


@celery_app.task(name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(
    context,
    batch_id=None,
    notification_type_name='blank',
    campaign_id=None,
    run_id=None,
    developer_reminder=False,
):
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    recipients_qs = NotificationCampaignRecipient.objects.filter(batch_id=batch_id).select_related('user')

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
            recipients_qs.update(
                status=NotificationCampaignRecipientStatus.FAILED,
                error_message='Notification type not found',
            )
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
            send_email_with_send_grid(
                to_addr=recipient_emails,
                notification_type=notification_type,
                context=context,
                is_multiple=True,
            )
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
        notification_campaign.save(update_fields=['sent_count', 'failed_count', 'updated_at'])

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
