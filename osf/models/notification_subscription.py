import logging
from django.utils import timezone
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from osf.models.notification_type import get_default_frequency_choices, NotificationType
from osf.models.notification import Notification
from api.base import settings
from api.base.utils import absolute_reverse
from django.core.validators import EmailValidator

from .base import BaseModel


class NotificationSubscription(BaseModel):
    notification_type = models.ForeignKey(
        'NotificationType',
        on_delete=models.CASCADE,
        null=True
    )
    user = models.ForeignKey(
        'osf.OSFUser',
        null=True,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    message_frequency: str = models.CharField(
        max_length=500,
        null=True
    )
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    subscribed_object = GenericForeignKey('content_type', 'object_id')

    # mark if subscription is for digest use only (instant subscriptions are sent every 5 minutes)
    _is_digest = models.BooleanField(default=False)

    def clean(self):
        ct = self.notification_type.object_content_type
        if ct:
            if self.content_type != ct and 'provider' not in self.notification_type.name.lower():
                raise ValidationError('Subscribed object must match type\'s content_type.')
            if not self.object_id:
                raise ValidationError('Subscribed object ID is required.')
        else:
            if self.content_type or self.object_id:
                raise ValidationError('Global subscriptions must not have an object.')

        allowed_freqs = self.notification_type.notification_interval_choices or get_default_frequency_choices()
        if self.message_frequency not in allowed_freqs:
            raise ValidationError(f'{self.message_frequency!r} is not allowed for {self.notification_type.name!r}.')

    def __str__(self) -> str:
        return (f'<{self.user} via {self.subscribed_object} subscribes to '
                f'{getattr(self.notification_type, 'name', 'MISSING')} ({self.message_frequency})>')

    class Meta:
        verbose_name = 'Notification Subscription'
        verbose_name_plural = 'Notification Subscriptions'
        db_table = 'osf_notificationsubscription_v2'
        unique_together = ('notification_type', 'user', 'content_type', 'object_id', '_is_digest')

    def emit(
            self,
            event_context=None,
            destination_address=None,
            email_context=None,
            save=True,
    ):
        """Emit a notification to a user by creating Notification and NotificationSubscription objects.

        Args:
            event_context (OSFUser): The info for context for the template
            destination_address (optional): overides the user's email address for the notification. Good for sending
            to a test address or OSF desk support'
            email_context (dict, optional): Context for sending the email bcc, reply_to header etc
            save (bool, optional): save the notification and creates a subscription object if true, otherwise just
            send the notification with no db transaction, therefore message_frequency should always be 'instantly' when
            used.
        """
        if not settings.CI_ENV:
            logging.info(
                f"Attempting to create Notification:"
                f"\nto={getattr(self.user, 'username', destination_address)}"
                f"\ntype={self.notification_type.name}"
                f"\nmessage_frequency={self.message_frequency}"
                f"\nevent_context={event_context}"
                f"\nemail_context={email_context}"
            )

        if not destination_address:
            destination_address = self.user.email
            validator = EmailValidator()
            try:
                validator(destination_address)
            except ValidationError:
                emails_qs = self.user.emails
                if emails_qs.exists():
                    destination_address = emails_qs.first().address
                try:
                    validator(destination_address)
                except ValidationError:
                    return

        if self.message_frequency == 'instantly':
            notification = Notification(
                subscription=self,
                event_context=event_context
            )
            if save:
                notification.save()
            else:
                notification.send(
                    destination_address=destination_address,
                    email_context=email_context,
                    save=save,
                )
                return
            if not self._is_digest:
                notification.send(
                    destination_address=destination_address,
                    email_context=email_context,
                    save=save,
                )
        else:
            Notification.objects.create(
                subscription=self,
                event_context=event_context,
                sent=timezone.now() if self.message_frequency == 'none' else None,
                fake_sent=True if self.message_frequency == 'none' else False,
            )

    @property
    def absolute_api_v2_url(self):
        return absolute_reverse(
            'subscriptions:notification-subscription-detail',
            kwargs={
                'subscription_id': self._id, 'version': 'v2'
            }
        )

    @property
    def _id(self):
        """
        Legacy subscription id for API compatibility.
        """
        _global_file_updated = [
            NotificationType.Type.USER_FILE_UPDATED.value,
            NotificationType.Type.FILE_UPDATED.value,
            NotificationType.Type.FILE_ADDED.value,
            NotificationType.Type.FILE_REMOVED.value,
            NotificationType.Type.ADDON_FILE_COPIED.value,
            NotificationType.Type.ADDON_FILE_RENAMED.value,
            NotificationType.Type.ADDON_FILE_MOVED.value,
            NotificationType.Type.ADDON_FILE_REMOVED.value,
            NotificationType.Type.FOLDER_CREATED.value,
        ]
        _global_reviews = [
            NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
            NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
            NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
        ]
        _node_file_updated = [
            NotificationType.Type.NODE_FILE_UPDATED.value,
            NotificationType.Type.FILE_ADDED.value,
            NotificationType.Type.FILE_REMOVED.value,
            NotificationType.Type.ADDON_FILE_COPIED.value,
            NotificationType.Type.ADDON_FILE_RENAMED.value,
            NotificationType.Type.ADDON_FILE_MOVED.value,
            NotificationType.Type.ADDON_FILE_REMOVED.value,
            NotificationType.Type.FOLDER_CREATED.value,
        ]
        if self.notification_type.name in _global_file_updated:
            return f'{self.user._id}_file_updated'
        elif self.notification_type.name in _global_reviews:
            return f'{self.user._id}_global_reviews'
        elif self.notification_type.name in _node_file_updated:
            return f'{self.subscribed_object._id}_file_updated'
        raise NotImplementedError()
