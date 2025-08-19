import logging

import waffle
from django.db import models
from django.utils import timezone

from api.base import settings as api_settings
from osf import email, features


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

    def send(
            self,
            protocol_type='email',
            destination_address=None,
            email_context=None,
            save=True,
    ):
        """

        """
        recipient_address = destination_address or self.subscription.user.username

        if not api_settings.CI_ENV:
            logging.info(
                f"Attempting to send Notification:"
                f"\nto={getattr(self.subscription.user, 'username', destination_address)}"
                f"\nat={destination_address}"
                f"\ntype={self.subscription.notification_type}"
                f"\ncontext={self.event_context}"
                f"\nemail={email_context}"
            )
        if protocol_type == 'email' and waffle.switch_is_active(features.ENABLE_MAILHOG):
            email.send_email_over_smtp(
                recipient_address,
                self.subscription.notification_type,
                self.event_context,
                email_context
            )
        elif protocol_type == 'email':
            email.send_email_with_send_grid(
                recipient_address,
                self.subscription.notification_type,
                self.event_context,
                email_context
            )
        else:
            raise NotImplementedError(f'protocol `{protocol_type}` is not supported.')

        if save:
            self.mark_sent()

    def mark_sent(self) -> None:
        self.sent = timezone.now()
        self.save(update_fields=['sent'])

    def mark_seen(self) -> None:
        raise NotImplementedError('mark_seen must be implemented by subclasses.')
        # self.seen = timezone.now()
        # self.save(update_fields=['seen'])

    def render(self) -> str:
        """Render the notification message using the event context."""
        template = self.subscription.notification_type.template
        if not template:
            raise ValueError('Notification type must have a template to render the notification.')
        notification = email.render_notification(template, self.event_context)
        return notification

    def __str__(self) -> str:
        return f'Notification for {self.subscription.user} [{self.subscription.notification_type.name}]'

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
