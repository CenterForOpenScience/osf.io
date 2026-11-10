import logging

from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.email import send_email
from osf.models import NotificationTypeEnum
from osf.models.notification_campaign import (
    NotificationCampaign,
    NotificationCampaignStatus,
)

logger = logging.getLogger(__name__)


def send_campaign_log_email(campaign, status, message):
    """Send a notification campaign status email."""
    log_email_recipients = campaign.metadata.get('execution', {}).get('log_email_recipients', '')
    recipients = [recipient.strip() for recipient in log_email_recipients.split(',') if recipient.strip()]
    for recipient in recipients:
        try:
            send_email(
                recipient_address=recipient,
                notification_type=NotificationTypeEnum.NOTIFICATION_CAMPAIGN_LOG.instance,
                event_context={'campaign_name': campaign.name, 'status': status, 'message': message},)
        except Exception as exc:
            logger.error(f"Failed to send error logs email for campaign {campaign.id}: {exc}")
            sentry.log_message(f"Failed to send error logs email for campaign {campaign.id}: {exc}")


@celery_app.task(name='email.send_campaign_log_email')
def send_campaign_log_email_task(campaign_id, status, message):
    """Send a campaign status email outside the request, for events triggered from the admin."""
    send_campaign_log_email(NotificationCampaign.objects.get(id=campaign_id), status, message)


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

    def sync_campaign_stats(self, campaign, *, save=True):
        from .recipients import get_campaign_recipient_stats

        stats = get_campaign_recipient_stats(campaign.id)
        campaign.recipient_count = stats['recipient_count']
        campaign.sent_count = stats['sent_count']
        campaign.failed_count = stats['failed_count']
        campaign.skipped_count = stats['skipped_count']
        if save:
            campaign.save(update_fields=[
                'recipient_count',
                'sent_count',
                'failed_count',
                'skipped_count',
                'updated_at',
            ])
        return stats

    def finish_campaign(self, campaign, status=None, send_log_email=True):
        """Sync recipient counters, set completed_at once, optionally update status, and save."""
        self.sync_campaign_stats(campaign, save=False)
        if campaign.completed_at is None:
            campaign.completed_at = timezone.now()
        if status is not None:
            campaign.status = status
        campaign.save()
        if send_log_email:
            status_label = campaign.get_status_display()
            send_campaign_log_email(campaign, status_label, f'Campaign finished with status {status_label}')
