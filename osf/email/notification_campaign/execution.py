import logging
from datetime import timedelta

from django.db.models import Case, CharField, Subquery, When
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.email import _render_email_html, get_sendgrid_client, send_email, send_email_with_send_grid
from osf.models import NotificationType, NotificationTypeEnum
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationCampaignRecipientStatus,
    NotificationCampaignStatus,
)
from website import settings

from .base import NotificationCampaignTask
from .recipients import assign_batch_id_to_recipients, first_email_subquery

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.process_campaign_retry')
def process_campaign_retry(self, campaign_id, run_id, use_sendgrid_webhook=False):
    """Attempt to retry failed recipients. This happens at the end of each campaign. If retry is successful, reaches max
    retry limit, or times out it will continue to finish the campaign (with respective status). If retry is blocked, it
    will kick off another retry. If campaign is canceled, it will skip and finish the campaign. Note: the retry actually
    calls `dispatch_campaign` to execute the one retry.
    """
    campaign = self.get_campaign(campaign_id, run_id, abort_if_cancelled=False)
    if campaign is None:
        message = f'[Notification Campaign #{campaign_id}] ERROR: Campaign retry failed due to campaign not found.'
        logger.error(message)
        sentry.log_message(message)
        return

    campaign.refresh_from_db()
    campaign_retry_attempt_started_at = timezone.now()
    campaign_retry_id = f'{campaign_id}-{run_id}-retry#{campaign.retries}'
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
               f'Campaign retry({campaign_retry_id}) attempted at {campaign_retry_attempt_started_at}.')
    logger.info(message)
    sentry.log_message(message)
    execution = campaign.metadata.get('execution', {})

    if campaign.status == NotificationCampaignStatus.CANCELLED:
        message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                   f'Campaign retry({campaign_retry_id}) attempt skipped due to campaign cancelled, '
                   f'and continue to finish campaign (as cancelled as it is).')
        logger.info(message)
        sentry.log_message(message)
        self.finish_campaign(campaign)
        return

    in_flight_qs = NotificationCampaignRecipient.objects.filter(
        campaign=campaign,
        status__in=[
            NotificationCampaignRecipientStatus.QUEUED,
            NotificationCampaignRecipientStatus.AWAITING_DELIVERY,
        ],
    )
    if in_flight_qs.exists():
        delivery_timeout = execution.get('delivery_timeout', settings.DEFAULT_CAMPAIGN_DELIVERY_TIMEOUT)
        reference_time = campaign.started_at or campaign.created_at
        if timezone.now() - reference_time < timedelta(seconds=delivery_timeout):
            # Still waiting for in-flight sends / SendGrid delivery webhooks.
            self.sync_campaign_stats(campaign)
            retry_interval = execution.get('dispatch_interval', settings.CAMPAIGN_DISPATCH_INTERVAL),
            message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                       f'Campaign retry({campaign_retry_id}) attempt skipped due to delivery in-progress, '
                       f'and kicking off another retry in {retry_interval}s.')
            logger.warning(message)
            sentry.log_message(message)
            process_campaign_retry.apply_async(
                kwargs={
                    'campaign_id': campaign_id,
                    'run_id': campaign.run_id,
                    'use_sendgrid_webhook': use_sendgrid_webhook,
                },
                countdown=retry_interval,
            )
            return

        timed_out_cout = in_flight_qs.update(
            status=NotificationCampaignRecipientStatus.FAILED,
            error_message='Delivery timeout'
        )
        message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                   f'Campaign retry({campaign_retry_id}) attempt skipped due to delivery timeout({delivery_timeout}s), '
                   f'and marked {timed_out_cout} queued/awaiting-delivery recipients as FAILED, '
                   f'and continue to finish campaign as {NotificationCampaignStatus.PARTIALLY_COMPLETED}')
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
            campaign_retry_exec_started_at = timezone.now()
            campaign.retries += 1
            message = (f'[Notification Campaign #{campaign_id}] INFO: '
                       f'Campaign retry({campaign_retry_id}) execution({campaign.retries}/{max_retries}) started '
                       f'at {campaign_retry_exec_started_at} with {failed_recipients_count} recipients.')
            logger.info(message)
            sentry.log_message(message)
            campaign.save()
            dispatch_campaign.apply_async(
                args=[campaign_id, campaign.run_id],
                kwargs={
                    'restart_failed': True,
                    'use_sendgrid_webhook': use_sendgrid_webhook,
                },
            )
            return
        final_status = NotificationCampaignStatus.PARTIALLY_COMPLETED
        message = (f'[Notification Campaign #{campaign_id}] WARNING: '
                   f'Campaign retry({campaign_retry_id}) finished with max retries reached, '
                   f'and continue to finish campaign as {NotificationCampaignStatus.PARTIALLY_COMPLETED}')
        logger.warning(message)
    else:
        final_status = NotificationCampaignStatus.COMPLETED
        message = (f'[Notification Campaign #{campaign_id}] INFO: '
                   f'Campaign retry({campaign_retry_id}) finished successfully, '
                   f'and continue to finish campaign as {NotificationCampaignStatus.COMPLETED}')
        logger.info(message)
    sentry.log_message(message)

    self.finish_campaign(campaign, final_status)

@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.start_notification_campaign')
def start_notification_campaign(self, campaign_id, restart_failed=False, restart_stuck=False):
    """The primary task that starts the campaign, restart stuck campaign or manually retry failed recipients.
    """
    campaign = self.get_campaign(campaign_id)
    if campaign is None:
        message = f'[Notification Campaign #{campaign_id}] ERROR: Campaign start failed due to campaign not found.'
        logger.error(message)
        sentry.log_message(message)
        return
    notification_type_name = campaign.notification_type.name

    # IMPORTANT: Clears notification type (email template) cache
    if hasattr(NotificationTypeEnum, notification_type_name):
        del getattr(NotificationTypeEnum, notification_type_name).instance

    if restart_stuck:
        # Only reclaim Celery-in-flight batches. Leave AWAITING_DELIVERY alone so that
        # SendGrid webhooks for already-accepted mail still match recipient.sent_at.
        NotificationCampaignRecipient.objects.filter(
            campaign_id=campaign_id,
            status=NotificationCampaignRecipientStatus.QUEUED,
        ).update(status=NotificationCampaignRecipientStatus.PENDING, batch_id=None)

    # Decide once per run which SendGrid user sends the campaign: bulk campaigns track delivery
    # via webhook, which requires the sub-user with Event Webhook enabled.
    use_sendgrid_webhook = bool(campaign.metadata.get('sendgrid_bulk', False))
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
               f'Campaign started successfully at {campaign.started_at}, '
               f'kicking off the first dispatcher (TASK: "dispatch_campaign").')
    logger.error(message)
    sentry.log_message(message)
    dispatch_campaign.apply_async(
        args=[campaign_id, campaign.run_id],
        kwargs={
            'restart_failed': restart_failed,
            'use_sendgrid_webhook': use_sendgrid_webhook,
        },
    )


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.dispatch_campaign')
def dispatch_campaign(self, campaign_id, run_id, restart_failed=False, restart_stuck=False, use_sendgrid_webhook=False):
    """The dispatching task that controls when to dispatch new batches/tasks (which actually sends the email). After
    each dispatch is done, it schedules another dispatching task (future self) and quits (current self), if there is
    still recipients to be processed. Otherwise, it kicks off the retry process to retry and finish up the campaign.
    """
    campaign = self.get_campaign(campaign_id, run_id)
    if campaign is None:
        message = f'[Notification Campaign #{campaign_id}] ERROR: Campaign dispatch failed due to campaign not found.'
        logger.error(message)
        sentry.log_message(message)
        return
    if campaign.status != NotificationCampaignStatus.RUNNING:
        message = (f'[Notification Campaign #{campaign_id}] ERROR: '
                   f'Campaign dispatch failed due to invalid status({campaign.status}), expecting RUNNING.')
        logger.error(message)
        sentry.log_message(message)
        return
    notification_type_name = campaign.notification_type.name

    # Refresh counters once per dispatch interval (covers SENT without webhook and
    # FAILED/SKIPPED set by batches) instead of re-aggregating after every batch.
    self.sync_campaign_stats(campaign)

    queued_batches_count = NotificationCampaignRecipient.objects.filter(
        campaign=campaign,
        batch_id__isnull=False,
        status=NotificationCampaignRecipientStatus.QUEUED
    ).order_by().values('batch_id').distinct().count()
    execution = campaign.metadata.get('execution', {})
    batch_size = execution.get('batch_size', settings.DEFAULT_CAMPAIGN_BATCH_SIZE)
    activity_threshold = execution.get('activity_threshold', settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD)
    max_queued_batches = execution.get('max_queued_batches', settings.MAX_QUEUED_CAMPAIGN_BATCHES)
    to_queue = max_queued_batches - queued_batches_count
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
               f'Dispatching {to_queue} new batches/tasks (TASK: "send_campaign_batch") ...')
    logger.info(message)
    sentry.log_message(message)

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
                use_sendgrid_webhook=use_sendgrid_webhook,
            )
            new_queued_batches += 1
        to_queue -= new_queued_batches
        total_new_queued_batches += new_queued_batches
        new_queued_batches = 0
        if to_queue <= 0:
            break

    if no_more_recipients:
        next_steps = 'continue to process campaign retry because all recipients has been dispatched successfully.'
        process_campaign_retry.delay(
            campaign_id=campaign_id, run_id=campaign.run_id, use_sendgrid_webhook=use_sendgrid_webhook
        )
    else:
        dispatch_interval = execution.get('dispatch_interval', settings.CAMPAIGN_DISPATCH_INTERVAL)
        next_steps = f'kicking off a new dispatcher in {dispatch_interval}s to dispatch more recipients.'
        self.apply_async(
            args=[campaign_id, run_id],
            kwargs={
                'restart_failed': restart_failed,
                'use_sendgrid_webhook': use_sendgrid_webhook,
            },
            countdown=dispatch_interval,
        )
    message = (f'[Notification Campaign #{campaign_id}] INFO: '
               f'Dispatched {total_new_queued_batches} new batches/tasks (TASK: "send_campaign_batch"), {next_steps}')
    logger.info(message)
    sentry.log_message(message)


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.send_campaign_batch', ignore_result=False)
def send_campaign_batch(
    self,
    context,
    batch_id=None,
    notification_type_name='blank',
    campaign_id=None,
    run_id=None,
    developer_reminder=False,
    use_sendgrid_webhook=False,
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
                self.send_campaign_log_email(campaign, message=message, status='WARNING')

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

    sendgrid_client = get_sendgrid_client(use_webhook=use_sendgrid_webhook)

    if campaign.metadata.get('sendgrid_bulk', False):
        recipients = list(valid_emails_qs)
        recipient_emails = []
        custom_args_list = []
        sent_at = int(timezone.now().timestamp())
        for recipient in recipients:
            recipient_emails.append(recipient.recipient_address)
            custom_args_list.append(
                {
                    'campaign_recipient_id': str(recipient.id),
                    'campaign_id': str(campaign_id),
                    'sent_at': str(sent_at),
                }
            )
        try:
            send_email_with_send_grid(
                to_addr=recipient_emails,
                notification_type=notification_type,
                context=context,
                email_context={'custom_args_list': custom_args_list},
                is_multiple=True,
                client=sendgrid_client,
            )
            valid_emails_qs.update(
                status=NotificationCampaignRecipientStatus.AWAITING_DELIVERY,
                sent_at=sent_at,
            )
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
            sent_at = int(notification_started_at.timestamp())
            try:
                send_email(
                    recipient_address=recipient.recipient_address,
                    notification_type=notification_type,
                    event_context=context,
                    email_context={
                        'custom_args': {
                            'campaign_recipient_id': str(recipient.id),
                            'campaign_id': str(campaign_id),
                            'sent_at': str(sent_at),
                        },
                    },
                    rendered_html=rendered_html,
                    client=sendgrid_client,
                )
                recipient.status = NotificationCampaignRecipientStatus.SENT
                recipient.error_message = None
                recipient.sent_at = sent_at
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
            NotificationCampaignRecipient.objects.bulk_update(recipient_records, ['status', 'error_message', 'sent_at'])

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
