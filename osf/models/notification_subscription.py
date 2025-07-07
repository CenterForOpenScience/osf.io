from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

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

    def clean(self):
        ct = self.notification_type.object_content_type

        if ct:
            if self.content_type != ct:
                raise ValidationError('Subscribed object must match type\'s content_type.')
            if not self.object_id:
                raise ValidationError('Subscribed object ID is required.')
        else:
            if self.content_type or self.object_id:
                raise ValidationError('Global subscriptions must not have an object.')
        from . import NotificationType

        allowed_freqs = self.notification_type.notification_interval_choices or NotificationType.DEFAULT_FREQUENCY_CHOICES
        if self.message_frequency not in allowed_freqs:
            raise ValidationError(f'{self.message_frequency!r} is not allowed for {self.notification_type.name!r}.')

    def __str__(self) -> str:
        return f'<{self.user} via {self.subscribed_object} subscribes to {self.notification_type.name} ({self.message_frequency})>'

    class Meta:
        verbose_name = 'Notification Subscription'
        verbose_name_plural = 'Notification Subscriptions'

    def emit(self, user, subscribed_object=None, event_context=None):
        """Emit a notification to a user by creating Notification and NotificationSubscription objects.

        Args:
            user (OSFUser): The recipient of the notification.
            subscribed_object (optional): The object the subscription is related to.
            event_context (dict, optional): Context for rendering the notification template.
        """
        from . import Notification

        if self.message_frequency == 'instantly':
            Notification.objects.create(
                subscription=self,
                event_context=event_context
            ).send()
        else:
            Notification.objects.create(
                subscription=self,
                event_context=event_context
            )

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def _id(self):
        """
        Legacy subscription id for API compatibility.
        Provider: <short_name>_<event>
        User/global: <user_id>_global_<event>
        Node/etc: <guid>_<event>
        """
        # Safety checks
        event = self.notification_type.name
        ct = self.notification_type.object_content_type
        match getattr(ct, 'model', None):
            case 'preprintprovider' | 'collectionprovider' | 'registrationprovider':
                # Providers: use subscribed_object._id (which is the provider short name, e.g. 'mindrxiv')
                return f'{self.subscribed_object._id}_new_pending_submissions'
            case 'node' | 'collection' | 'preprint':
                # Node-like objects: use object_id (guid)
                return f'{self.subscribed_object._id}_{event}'
            case 'osfuser' | 'user' | None:
                # Global: <user_id>_global
                return f'{self.user._id}_global'
            case _:
                raise NotImplementedError()
