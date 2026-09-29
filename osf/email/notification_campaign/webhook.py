from django.db import transaction
from django.db.models import Case, TextField, Value, When

from framework.celery_tasks import app as celery_app
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignRecipient,
    NotificationCampaignRecipientStatus,
)

from .base import NotificationCampaignTask

# Flattened onto SendGrid Event Webhook payloads via personalization custom_args.
CAMPAIGN_CUSTOM_ARG_KEYS = ('campaign_id', 'campaign_recipient_id', 'run_id')
SENDGRID_SUCCESS_EVENTS = frozenset({'delivered'})
# Permanent / non-retryable delivery failures → SKIPPED (excluded from restart_failed).
SENDGRID_SKIP_EVENTS = frozenset({'dropped'})
# Soft / retryable failures → FAILED (eligible for campaign retry).
SENDGRID_SOFT_BOUNCE_TYPE = 'blocked'
SENDGRID_HARD_BOUNCE_TYPE = 'bounce'


def _sendgrid_event_error_message(event):
    return event.get('reason') or event.get('type') or event.get('event') or 'SendGrid delivery failed'


def _classify_sendgrid_failure(event):
    """Return SKIPPED/FAILED status for a failure event, or None to ignore.

    - ``dropped`` / hard ``bounce`` (type ``bounce`` or missing): permanent → SKIPPED
    - soft ``bounce`` (type ``blocked``): transient → FAILED (campaign may retry)
    - ``deferred`` and other events: ignored (SendGrid keeps retrying deferred)
    """
    event_type = event.get('event')
    if event_type in SENDGRID_SKIP_EVENTS:
        return NotificationCampaignRecipientStatus.SKIPPED
    if event_type == 'bounce':
        bounce_type = event.get('type') or SENDGRID_HARD_BOUNCE_TYPE
        if bounce_type == SENDGRID_SOFT_BOUNCE_TYPE:
            return NotificationCampaignRecipientStatus.FAILED
        return NotificationCampaignRecipientStatus.SKIPPED
    return None


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.process_sendgrid_campaign_events')
def process_sendgrid_campaign_events(self, events):
    """Update campaign recipients from filtered SendGrid Event Webhook events.

    Expects events that already include campaign ``custom_args``
    (``campaign_id``, ``campaign_recipient_id``, ``run_id``). Only
    ``AWAITING_DELIVERY``, ``FAILED``, or ``SKIPPED`` recipients whose event
    ``run_id`` matches the campaign's current run are updated; delayed
    webhooks from a prior run are ignored.

    Permanent failures (``dropped``, hard bounce) become ``SKIPPED`` so
    ``restart_failed`` will not resend them. Soft bounces (``type=blocked``)
    become ``FAILED`` and remain retryable. ``deferred`` events are ignored
    (SendGrid retries those itself).

    A ``delivered`` event wins over failure events for the same recipient
    (including a prior ``FAILED``/``SKIPPED`` from an earlier webhook) so a
    confirmed delivery is never left failed (and retried).
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
    skipped = dict()

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
            skipped.pop(recipient_pk, None)
            continue

        failure_status = _classify_sendgrid_failure(event)
        if failure_status is None or recipient_pk in success_ids:
            continue

        error_message = _sendgrid_event_error_message(event)
        if failure_status == NotificationCampaignRecipientStatus.SKIPPED:
            skipped[recipient_pk] = error_message
            failed.pop(recipient_pk, None)
        else:
            failed[recipient_pk] = error_message
            skipped.pop(recipient_pk, None)

    if not success_ids and not failed and not skipped:
        return

    with transaction.atomic():
        # Lock campaign rows so concurrent webhook/batch syncs cannot overwrite
        # counters with a stale aggregate snapshot.
        campaigns = list(
            NotificationCampaign.objects.select_for_update()
            .filter(id__in=campaign_ids)
            .order_by('id')
        )
        if success_ids:
            NotificationCampaignRecipient.objects.filter(
                id__in=success_ids,
                status__in=[
                    NotificationCampaignRecipientStatus.AWAITING_DELIVERY,
                    NotificationCampaignRecipientStatus.FAILED,
                    NotificationCampaignRecipientStatus.SKIPPED,
                ],
            ).update(status=NotificationCampaignRecipientStatus.SENT, error_message=None)

        if failed:
            failed_errors = [
                When(id=recipient_pk, then=Value(error_message))
                for recipient_pk, error_message in failed.items()
            ]
            NotificationCampaignRecipient.objects.filter(
                id__in=failed.keys(),
                status=NotificationCampaignRecipientStatus.AWAITING_DELIVERY,
            ).update(
                status=NotificationCampaignRecipientStatus.FAILED,
                error_message=Case(
                    *failed_errors,
                    default=Value('SendGrid delivery failed'),
                    output_field=TextField(),
                ),
            )

        if skipped:
            skipped_errors = [
                When(id=recipient_pk, then=Value(error_message))
                for recipient_pk, error_message in skipped.items()
            ]
            NotificationCampaignRecipient.objects.filter(
                id__in=skipped.keys(),
                status=NotificationCampaignRecipientStatus.AWAITING_DELIVERY,
            ).update(
                status=NotificationCampaignRecipientStatus.SKIPPED,
                error_message=Case(
                    *skipped_errors,
                    default=Value('SendGrid delivery skipped'),
                    output_field=TextField(),
                ),
            )

        for campaign in campaigns:
            self.sync_campaign_stats(campaign)
