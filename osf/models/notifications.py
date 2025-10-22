from django.db import models

from .base import BaseModel


class NotificationSubscriptionLegacy(BaseModel):
    primary_identifier_name = '_id'
    _id = models.CharField(max_length=100, db_index=True, unique=False)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = models.CharField(max_length=100)  # wiki_updated, comment_replies

    user = models.ForeignKey('OSFUser', related_name='notification_subscriptions',
                             null=True, blank=True, on_delete=models.CASCADE)
    node = models.ForeignKey('Node', related_name='notification_subscriptions',
                             null=True, blank=True, on_delete=models.CASCADE)
    provider = models.ForeignKey('AbstractProvider', related_name='notification_subscriptions',
                                 null=True, blank=True, on_delete=models.CASCADE)
    # Notification types
    none = models.ManyToManyField('OSFUser', related_name='+')  # reverse relationships
    email_digest = models.ManyToManyField('OSFUser', related_name='+')  # for these
    email_transactional = models.ManyToManyField('OSFUser', related_name='+')  # are pointless

    class Meta:
        # Both PreprintProvider and RegistrationProvider default instances use "osf" as their `_id`
        unique_together = ('_id', 'provider')
        db_table = 'osf_notificationsubscription_legacy'
