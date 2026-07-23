from django.db import models
from django.utils import timezone
import uuid


class NotificationCampaignStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    RUNNING = 'running', 'Running'
    COMPLETED = 'completed', 'Completed'
    PARTIALLY_COMPLETED = 'partially_completed', 'Partially Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    ENDED = 'ended', 'Ended'

class NotificationCampaignRecipientStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    FAILED = 'failed', 'Failed'
    SKIPPED = 'skipped', 'Skipped'
    POSTPONED = 'postponed', 'Postponed'


class NotificationCampaign(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    run_id = models.UUIDField(null=True, blank=True, unique=True)

    name = models.CharField(max_length=255)

    notification_type = models.ForeignKey(
        'NotificationType',
        on_delete=models.PROTECT,
    )
    created_by = models.ForeignKey(
        'OSFUser',
        null=True,
        on_delete=models.SET_NULL,
    )

    status = models.CharField(
        max_length=20,
        choices=NotificationCampaignStatus.choices,
        default=NotificationCampaignStatus.CREATED,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    # metadata structure:
    # {
    #   "filters": {
    #     ...
    #   },
    #   "context": {
    #     ...
    #   },
    #   "execution": {
    #     "batch_size": <int>,
    #     "max_retries": <int>,
    #     "activity_threshold": <int>,
    #   },
    #   "template": <str>,
    # }

    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    retries = models.PositiveIntegerField(default=0)

    developer_reminder_sent = models.BooleanField(default=False)

    def start(self, restart_failed=False):
        from osf.email.notification_campaign import start_notification_campaign
        self.status = NotificationCampaignStatus.RUNNING
        self.started_at = timezone.now()
        self.run_id = uuid.uuid4()
        if not restart_failed:
            self.recipient_count = 0
            self.sent_count = 0
        self.failed_count = 0
        self.retries = 0
        self.metadata.update({'template': self.notification_type.template})
        self.save()
        start_notification_campaign.delay(campaign_id=self.id, restart_failed=restart_failed)


class NotificationCampaignRecipient(models.Model):
    campaign = models.ForeignKey(
        NotificationCampaign,
        on_delete=models.CASCADE,
        related_name='recipients',
    )
    user = models.ForeignKey(
        'OSFUser',
        on_delete=models.CASCADE,
    )
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationCampaignRecipientStatus.choices,
        default=NotificationCampaignRecipientStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(null=True, blank=True)

    activity_score = models.IntegerField(default=0)

    class Meta:
        unique_together = ('campaign', 'user')
        ordering = [
            '-activity_score',
            'user__date_registered',
            'user_id',
        ]

        indexes = [
            models.Index(
                fields=[
                    'campaign',
                    '-activity_score',
                    'user',
                ],
                name='campaign_order_idx',
            ),
            models.Index(
                fields=[
                    'campaign',
                    'status',
                    '-activity_score',
                    'user',
                ],
                name='campaign_status_order_idx',
            ),
        ]
