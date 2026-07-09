from django.db import models
from django.utils import timezone


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


class NotificationCampaign(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    #   },
    #   "template": <str>,
    # }

    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    retries = models.PositiveIntegerField(default=0)

    def start(self):
        from osf.email.notification_campaign import start_notification_campaign
        self.status = NotificationCampaignStatus.RUNNING
        self.started_at = timezone.now()

        self.sent_count = 0
        self.failed_count = 0
        self.recipient_count = 0
        self.retries = 0
        self.metadata.update({'template': self.notification_type.template})
        self.save()
        start_notification_campaign.delay(campaign_id=self.id)


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

    class Meta:
        unique_together = ('campaign', 'user')
