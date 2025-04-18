from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.template import Template, TemplateSyntaxError
from django.utils import timezone
from .base import BaseModel
OSFUser = get_user_model()


class NotificationType(models.Model):
    FREQUENCY_CHOICES = [
        ('none', 'None'),
        ('instantly', 'Instantly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    name: str = models.CharField(max_length=255, unique=True)
    notification_freq: str = models.CharField(
        max_length=32,
        choices=FREQUENCY_CHOICES,
        default='instantly',
    )

    object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Content type for subscribed objects. Null means global event.'
    )

    template: str = models.TextField(
        help_text='Template used to render the event_info. Supports Django template syntax.'
    )

    def clean(self):
        try:
            Template(self.template)
        except TemplateSyntaxError as exc:
            raise ValidationError({'template': f'Invalid template: {exc}'})

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Notification Type'
        verbose_name_plural = 'Notification Types'


class NotificationSubscription(BaseModel):
    notification_type: NotificationType = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        null=False
    )
    user: OSFUser = models.ForeignKey(OSFUser, on_delete=models.CASCADE, related_name='subscriptions')
    message_frequency: str = models.CharField(max_length=32)

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

        if self.message_frequency not in self.notification_type.notification_freq:
            raise ValidationError(f'{self.message_frequency!r} is not allowed for {self.notification_type.name!r}.')

    def __str__(self) -> str:
        return f'{self.user} subscribes to {self.notification_type.name} ({self.message_frequency})'

    def emit(self):
        from framework.auth.views import mails

        mails.send_mail(
            self.user.username,
            self.notification_type.template,
        )

    class Meta:
        verbose_name = 'Notification Subscription'
        verbose_name_plural = 'Notification Subscriptions'


class Notification(models.Model):
    subscription = models.ForeignKey(
        NotificationSubscription,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_info: dict = models.JSONField()
    sent = models.DateTimeField(null=True, blank=True)
    seen = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def mark_sent(self) -> None:
        self.sent = timezone.now()
        self.save(update_fields=['sent'])

    def mark_seen(self) -> None:
        self.seen = timezone.now()
        self.save(update_fields=['seen'])

    def __str__(self) -> str:
        return f'Notification for {self.subscription.user} [{self.subscription.notification_type.name}]'

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
