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
    created = models.DateTimeField(auto_now_add=True)
    fake_sent = models.BooleanField(default=False)

    def send(
            self,
            protocol_type='email',
            destination_address=None,
            email_context=None,
            save=True,
    ):
        recipient_address = destination_address or self.subscription.user.email or self.subscription.user.emails.first().address
        if not api_settings.CI_ENV:
            logging.info(
                f"Attempting to send Notification:"
                f"\nto={getattr(self.subscription.user, 'username', destination_address)}"
                f"\nat={recipient_address}"
                f"\ntype={self.subscription.notification_type}"
                f"\ncontext={self.event_context}"
                f"\nemail_context={email_context}"
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

    def mark_sent(self, fake_sent=False) -> None:
        update_fields = ['sent']
        self.sent = timezone.now()
        if fake_sent:
            update_fields.append('fake_sent')
            self.fake_sent = True
        self.save(update_fields=update_fields)

    def render(self) -> str:
        """Render the notification message using the event context."""
        notification_type = self.subscription.notification_type
        if not notification_type:
            raise ValueError('Notification type must have a template to render the notification.')
        notification = email._render_email_html(notification_type, self.event_context)
        return notification

    def __str__(self) -> str:
        return f'Notification for {self.subscription.user} [{self.subscription.notification_type.name}]'

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
