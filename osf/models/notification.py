import logging

from django.db import models
from website import settings
from api.base import settings as api_settings
from osf import email

class Notification(models.Model):
    subscription = models.ForeignKey(
        'NotificationSubscription',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_context: dict = models.JSONField()
    sent = models.DateTimeField(null=True, blank=True)
    seen = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def send(self, protocol_type='email', recipient=None):
        if not settings.USE_EMAIL:
            return
        if not protocol_type == 'email':
            raise NotImplementedError(f'Protocol type {protocol_type}. Email notifications are only implemented.')

        recipient_address = getattr(recipient, 'username', None) or self.subscription.user

        if protocol_type == 'email' and settings.DEV_MODE and settings.ENABLE_TEST_EMAIL:
            email.send_email_over_smtp(
                recipient_address,
                self.subscription.notification_type,
                self.event_context
            )
        elif protocol_type == 'email' and settings.DEV_MODE:
            if not api_settings.CI_ENV:
                logging.info(
                    f"Attempting to send email in DEV_MODE with ENABLE_TEST_EMAIL false just logs:"
                    f"\nto={recipient_address}"
                    f"\ntype={self.subscription.notification_type.name}"
                    f"\ncontext={self.event_context}"
                )
        elif protocol_type == 'email':
            email.send_email_with_send_grid(
                getattr(recipient, 'username', None) or self.subscription.user,
                self.subscription.notification_type,
                self.event_context
            )
        else:
            raise NotImplementedError(f'protocol `{protocol_type}` is not supported.')

        self.mark_sent()

    def mark_sent(self) -> None:
        raise NotImplementedError('mark_sent must be implemented by subclasses.')
        # self.sent = timezone.now()
        # self.save(update_fields=['sent'])

    def mark_seen(self) -> None:
        raise NotImplementedError('mark_seen must be implemented by subclasses.')
        # self.seen = timezone.now()
        # self.save(update_fields=['seen'])

    def __str__(self) -> str:
        return f'Notification for {self.subscription.user} [{self.subscription.notification_type.name}]'

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
