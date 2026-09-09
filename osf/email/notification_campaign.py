import logging
import uuid
from osf.models import NotificationType, NotificationTypeEnum, OSFUser, UserActivityCounter, Email
from osf.models.spam import SpamStatus
from django.db import transaction
from django.db.models import OuterRef, Subquery, Case, When, Value, CharField, Count, Q, BooleanField, TextField
from django.db.models.functions import Coalesce
from framework.celery_tasks import app as celery_app
from django.utils import timezone
from datetime import timedelta
from osf.models.notification_campaign import NotificationCampaign, NotificationCampaignRecipient, NotificationCampaignStatus, NotificationCampaignRecipientStatus
from osf.email import send_email_with_send_grid, _render_email_html, send_email
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

# Flattened onto SendGrid Event Webhook payloads via personalization custom_args.
CAMPAIGN_CUSTOM_ARG_KEYS = ('campaign_id', 'campaign_recipient_id', 'run_id')
SENDGRID_SUCCESS_EVENTS = frozenset({'delivered'})
SENDGRID_FAILURE_EVENTS = frozenset({'bounce', 'dropped'})

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


class NotificationCampaignTask(celery_app.Task):
    """Shared guards for notification campaign Celery tasks."""

    abstract = True

    def get_campaign(self, campaign_id, run_id=None, *, abort_if_cancelled=True):
        """Load a campaign, or return None if the task should no-op.
        """
        campaign = NotificationCampaign.objects.get(id=campaign_id)
        if run_id is not None and campaign.run_id != run_id:
            return None
        if abort_if_cancelled and campaign.status == NotificationCampaignStatus.CANCELLED:
            logger.warning(f"Campaign {campaign_id} was cancelled")
            return None
        return campaign

    def sync_campaign_stats(self, campaign):
        stats = get_campaign_recipient_stats(campaign.id)
        campaign.recipient_count = stats['recipient_count']
        campaign.sent_count = stats['sent_count']
        campaign.failed_count = stats['failed_count']
        return stats

    def finish_campaign(self, campaign, status=None):
        """Sync recipient counters, set completed_at once, optionally update status, and save."""
        self.sync_campaign_stats(campaign)
        if campaign.completed_at is None:
            campaign.completed_at = timezone.now()
        if status is not None:
            campaign.status = status
        campaign.save()


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

@celery_app.task(name='email.create_campaign_recipients')
def create_campaign_recipients(filters=None, campaign_id=None):
    recipients_creation_started_at = timezone.now()
    campaign = NotificationCampaign.objects.get(id=campaign_id)
    if not filters:

        raw_filters = campaign.metadata.get('filters', {})
        filters = build_campaign_filter_query(raw_filters)

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
            update_conflicts=True,
            update_fields=['activity_score'],
            unique_fields=['campaign', 'user'],
        )

    campaign.recipient_count = NotificationCampaignRecipient.objects.filter(campaign_id=campaign_id).count()
    campaign.metadata['recipients_creation_finished'] = True
    campaign.save(update_fields=['recipient_count', 'metadata'])

    recipients_creation_finished_at = timezone.now()
    recipients_creation_run_time = (recipients_creation_finished_at - recipients_creation_started_at)
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
                f'Recipients creation finished in {recipients_creation_run_time} seconds '
                f'(start={recipients_creation_started_at}, finish={recipients_creation_finished_at}) '
                f'for Campaign {campaign.name} (start={campaign.started_at}).')
    logger.info(message)
    sentry.log_message(message)


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


@celery_app.task(name='email.process_sendgrid_campaign_events')
def process_sendgrid_campaign_events(events):
    """Update campaign recipients from filtered SendGrid Event Webhook events.

    Expects events that already include campaign ``custom_args``
    (``campaign_id``, ``campaign_recipient_id``, ``run_id``). Only ``QUEUED``
    recipients whose event ``run_id`` matches the campaign's current run are
    updated; delayed webhooks from a prior run are ignored.

    A ``delivered`` event wins over failure events for the same recipient so a
    confirmed delivery is never marked failed (and retried).
    """
    campaign_ids = {
        event.get('campaign_id')
        for event in events
        if event.get('campaign_id', False)
    }
    if not campaign_ids:
        return

    current_run_ids = {
        str(campaign.id): str(campaign.run_id)
        for campaign in NotificationCampaign.objects.filter(
            id__in=campaign_ids,
            run_id__isnull=False,
        )
    }
    if not current_run_ids:
        return

    success_ids = set()
    failed = dict()

    for event in events:
        campaign_id = event.get('campaign_id', '')
        current_run_id = current_run_ids.get(str(campaign_id), None)
        if current_run_id is None or event.get('run_id') != current_run_id:
            continue

        event_type = event.get('event')
        recipient_id = event.get('campaign_recipient_id')
        if not recipient_id:
            continue
        try:
            recipient_pk = int(recipient_id)
        except (TypeError, ValueError):
            continue

        if event_type in SENDGRID_SUCCESS_EVENTS:
            success_ids.add(recipient_pk)
            failed.pop(recipient_pk, None)
        elif event_type in SENDGRID_FAILURE_EVENTS:
            if recipient_pk in success_ids:
                continue
            error_message = event.get('reason') or event.get('type') or event_type
            failed[recipient_pk] = error_message

    if success_ids:
        NotificationCampaignRecipient.objects.filter(
            id__in=success_ids,
            status=NotificationCampaignRecipientStatus.QUEUED,
        ).update(status=NotificationCampaignRecipientStatus.SENT, error_message=None)

    if failed:
        failed_errors = [
            When(id=recipient_pk, then=Value(error_message))
            for recipient_pk, error_message in failed.items()
        ]
        NotificationCampaignRecipient.objects.filter(
            id__in=failed.keys(),
            status=NotificationCampaignRecipientStatus.QUEUED,
        ).update(
            status=NotificationCampaignRecipientStatus.FAILED,
            error_message=Case(
                *failed_errors,
                default=Value('SendGrid delivery failed'),
                output_field=TextField(),
            ),
        )


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.process_campaign_retry')
def process_campaign_retry(self, campaign_id, run_id):
    campaign = self.get_campaign(campaign_id, run_id, abort_if_cancelled=False)
    if campaign is None:
        return

    campaign.refresh_from_db()
    execution = campaign.metadata.get('execution', {})

    if campaign.status == NotificationCampaignStatus.CANCELLED:
        message = f'[Notification Campaign #{campaign_id}] WARNING: Campaign {campaign.name} was cancelled.'
        logger.info(message)
        sentry.log_message(message)
        self.finish_campaign(campaign)
        return

    queued_qs = NotificationCampaignRecipient.objects.filter(
        campaign=campaign,
        status=NotificationCampaignRecipientStatus.QUEUED,
    )
    if queued_qs.exists():
        delivery_timeout = execution.get('delivery_timeout', settings.DEFAULT_CAMPAIGN_DELIVERY_TIMEOUT)
        reference_time = campaign.started_at or campaign.created_at
        if timezone.now() - reference_time < timedelta(seconds=delivery_timeout):
            # Still waiting for in-flight sends / SendGrid delivery webhooks.
            self.sync_campaign_stats(campaign)
            campaign.save()
            process_campaign_retry.apply_async(
                kwargs={'campaign_id': campaign_id, 'run_id': campaign.run_id},
                countdown=execution.get('dispatch_interval', settings.CAMPAIGN_DISPATCH_INTERVAL),
            )
            return

        timed_out = queued_qs.update(
            status=NotificationCampaignRecipientStatus.FAILED,
            error_message='SendGrid delivery timeout',
        )
        message = (
            f'[Notification Campaign #{campaign_id}] WARNING: '
            f'Marked {timed_out} queued recipients as FAILED after delivery timeout '
            f'({delivery_timeout}s) for campaign {campaign.name}.'
        )
        logger.warning(message)
        sentry.log_message(message)

        # Do not retry timed-out deliveries; close the run as partially completed.
        self.finish_campaign(campaign, NotificationCampaignStatus.PARTIALLY_COMPLETED)
        return

    failed_recipients_count = NotificationCampaignRecipient.objects.filter(
        campaign=campaign,
        status=NotificationCampaignRecipientStatus.FAILED,
    ).count()
    max_retries = execution.get('max_retries', settings.DEFAULT_CAMPAIGN_MAX_RETRIES)

    if failed_recipients_count:
        if campaign.retries < max_retries:
            message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                       f'Retrying {failed_recipients_count} failed recipients, '
                       f'previous retry attempts: {campaign.retries}/{max_retries}')
            logger.info(message)
            sentry.log_message(message)
            campaign.retries += 1
            campaign.save()

            dispatch_campaign.apply_async(
                args=[campaign_id, campaign.run_id],
                kwargs={
                    'restart_failed': True,
                },
            )
            return

        final_status = NotificationCampaignStatus.PARTIALLY_COMPLETED
    else:
        final_status = NotificationCampaignStatus.COMPLETED

    self.finish_campaign(campaign, final_status)

@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.start_notification_campaign')
def start_notification_campaign(self, campaign_id, restart_failed=False, restart_stuck=False):
    campaign = self.get_campaign(campaign_id)
    if campaign is None:
        return
    notification_type_name = campaign.notification_type.name

    if hasattr(NotificationTypeEnum, notification_type_name):
        del getattr(NotificationTypeEnum, notification_type_name).instance

    if restart_stuck:
        NotificationCampaignRecipient.objects.filter(
            campaign_id=campaign_id,
            status=NotificationCampaignRecipientStatus.QUEUED
        ).update(status=NotificationCampaignRecipientStatus.PENDING, batch_id=None)

    dispatch_campaign.apply_async(
        args=[campaign_id, campaign.run_id],
        kwargs={
            'restart_failed': restart_failed,
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

@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.dispatch_campaign')
def dispatch_campaign(self, campaign_id, run_id, restart_failed=False, restart_stuck=False):
    campaign = self.get_campaign(campaign_id, run_id)
    if campaign is None:
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
            'developer_reminder': True,
        },
        {
            'max_activity': activity_threshold,
            'spam': False,
            'developer_reminder': False,
        },
        {
            'spam': True,
            'developer_reminder': False,
        },
    )
    total_new_queued_batches = 0
    new_queued_batches = 0
    no_more_recipients = False
    for priority_group in priority_groups:
        no_more_recipients = False
        developer_reminder = priority_group.pop('developer_reminder', False)
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
                developer_reminder=developer_reminder,
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
            },
            countdown=execution.get('dispatch_interval', settings.CAMPAIGN_DISPATCH_INTERVAL),
        )


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(
    self,
    context,
    batch_id=None,
    notification_type_name='blank',
    campaign_id=None,
    run_id=None,
    developer_reminder=False,
):
    campaign = self.get_campaign(campaign_id, run_id)
    if campaign is None:
        return

    recipients_qs = NotificationCampaignRecipient.objects.filter(batch_id=batch_id).select_related('user')

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
        recipients = list(valid_emails_qs)
        recipient_emails = []
        custom_args_list = []
        for recipient in recipients:
            recipient_emails.append(recipient.recipient_address)
            custom_args_list.append(
                {
                    'campaign_recipient_id': str(recipient.id),
                    'campaign_id': str(campaign_id),
                    'run_id': str(run_id),
                }
            )
        try:
            send_email_with_send_grid(
                to_addr=recipient_emails,
                notification_type=notification_type,
                context=context,
                email_context={'custom_args_list': custom_args_list},
                is_multiple=True,
            )
            # Leave QUEUED until SendGrid Event Webhook confirms delivery.
        except Exception as exc:
            message = (f'[Notification Campaign #{campaign_id}] ERROR: '
                       f'Campaign {campaign.name} sendgrid bulk request failed, error={str(exc)}')
            logger.error(message)
            sentry.log_message(message)
            valid_emails_qs.update(status=NotificationCampaignRecipientStatus.FAILED, error_message=str(exc))
    else:
        rendered_html = _render_email_html(notification_type, context)
        for recipient in valid_emails_qs:
            notification_started_at = timezone.now()
            try:
                send_email(
                    recipient_address=recipient.recipient_address,
                    notification_type=notification_type,
                    event_context=context,
                    email_context={
                        'custom_args': {
                            'campaign_recipient_id': str(recipient.id),
                            'campaign_id': str(campaign_id),
                            'run_id': str(run_id),
                        },
                    },
                    rendered_html=rendered_html,
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
        if recipient_records:
            NotificationCampaignRecipient.objects.bulk_update(recipient_records, ['status', 'error_message'])

    # Lock the campaign row so concurrent batches cannot overwrite counters with a stale aggregate snapshot
    with transaction.atomic():
        notification_campaign = NotificationCampaign.objects.select_for_update().get(pk=campaign_id)
        self.sync_campaign_stats(notification_campaign)
        notification_campaign.save(update_fields=['sent_count', 'failed_count', 'recipient_count', 'updated_at'])

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
