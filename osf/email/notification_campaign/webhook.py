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
CAMPAIGN_CUSTOM_ARG_KEYS = ('campaign_id', 'campaign_recipient_id', 'sent_at')
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


def _classify_sendgrid_events(events, recipients):
    """Classify SendGrid events into success/failure/skipped categories."""
    successed = set()
    failed = dict()
    skipped = dict()

    for event in events:
        recipient_pk = event.get('campaign_recipient_id')
        if recipient_pk is None:
            continue

        recipient = recipients.get(int(recipient_pk))
        if recipient is None:
            continue

        if (
            recipient.sent_at is None
            or str(recipient.campaign_id) != str(event.get('campaign_id', ''))
            or str(recipient.sent_at) != str(event.get('sent_at', ''))
        ):
            continue

        event_type = event.get('event')
        if event_type in SENDGRID_SUCCESS_EVENTS:
            successed.add(recipient_pk)
            failed.pop(recipient_pk, None)
            skipped.pop(recipient_pk, None)
            continue

        failure_status = _classify_sendgrid_failure(event)
        if failure_status is None or recipient_pk in successed:
            continue

        error_message = _sendgrid_event_error_message(event)
        if failure_status == NotificationCampaignRecipientStatus.SKIPPED:
            skipped[recipient_pk] = error_message
            failed.pop(recipient_pk, None)
        else:
            failed[recipient_pk] = error_message
            skipped.pop(recipient_pk, None)

    return successed, failed, skipped


@celery_app.task(bind=True, base=NotificationCampaignTask, name='email.process_sendgrid_campaign_events')
def process_sendgrid_campaign_events(self, events):
    """Update campaign recipients from filtered SendGrid Event Webhook events.

    Expects events that already include campaign ``custom_args``
    (``campaign_id``, ``campaign_recipient_id``, ``sent_at``). Only
    ``AWAITING_DELIVERY`` or ``FAILED`` recipients whose event ``sent_at``
    matches the recipient's stored send stamp are updated; delayed webhooks
    from a prior send (e.g. after ``restart_failed``) are ignored.

    Permanent failures (``dropped``, hard bounce) become ``SKIPPED`` so
    ``restart_failed`` will not resend them. Soft bounces (``type=blocked``)
    become ``FAILED`` and remain retryable. ``deferred`` events are ignored
    (SendGrid retries those itself).

    A ``delivered`` event wins over failure events for the same recipient
    (including a prior ``FAILED``/``SKIPPED`` from an earlier webhook) so a
    confirmed delivery is never left failed (and retried).
    """
    campaign_ids = {
        int(campaign_id)
        for event in events
        if (campaign_id := event.get('campaign_id')) is not None
    }
    if not campaign_ids:
        return

    recipient_ids = {
        int(recipient_id)
        for event in events
        if (recipient_id := event.get('campaign_recipient_id')) is not None
    }
    recipients_by_id = {
        recipient.id: recipient
        for recipient in NotificationCampaignRecipient.objects.filter(
            id__in=recipient_ids,
        ).only('id', 'campaign_id', 'sent_at')
    }
    if not recipients_by_id:
        return

    success_ids, failed, skipped = _classify_sendgrid_events(events, recipients_by_id)
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
