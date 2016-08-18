from django.contrib.postgres.fields import ArrayField
from django.db import models
from osf_models.models import Node
from osf_models.models.base import BaseModel, ObjectIDMixin
from osf_models.models.validators import validate_subscription_type
from website.notifications.constants import NOTIFICATION_TYPES


class NotificationSubscription(BaseModel):
    _id = models.CharField(max_length=50, db_index=True)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = models.CharField(max_length=50)  # wiki_updated, comment_replies

    user = models.ForeignKey('OSFUser', null=True, related_name='notification_subscriptions')
    node = models.ForeignKey('Node', null=True)

    # Notification types
    none = models.ManyToManyField('OSFUser', related_name='+')  # reverse relationships
    email_digest = models.ManyToManyField('OSFUser', related_name='+')  # for these
    email_transactional = models.ManyToManyField('OSFUser', related_name='+')  # are pointless

    @property
    def owner(self):
        # ~100k have owner==user
        if self.user is not None:
            return self.user
        # ~8k have owner=Node
        elif self.node is not None:
            return self.node

    def add_user_to_subscription(self, user, notification_type, save=True):
        for nt in NOTIFICATION_TYPES:
            if user in getattr(self, nt):
                if nt != notification_type:
                    getattr(self, nt).remove(user)
            else:
                if nt == notification_type:
                    getattr(self, nt).append(user)

        if notification_type != 'none' and isinstance(self.owner, Node) and self.owner.parent_node:
            user_subs = self.owner.parent_node.child_node_subscriptions
            if self.owner._id not in user_subs.setdefault(user._id, []):
                user_subs[user._id].append(self.owner._id)
                self.owner.parent_node.save()

        if save:
            self.save()

    def remove_user_from_subscription(self, user, save=True):
        for notification_type in NOTIFICATION_TYPES:
            try:
                getattr(self, notification_type, []).remove(user)
            except ValueError:
                pass

        if isinstance(self.owner, Node) and self.owner.parent_node:
            try:
                self.owner.parent_node.child_node_subscriptions.get(user._id, []).remove(self.owner._id)
                self.owner.parent_node.save()
            except ValueError:
                pass

        if save:
            self.save()

class NotificationDigest(ObjectIDMixin, BaseModel):
    user = models.ForeignKey('OSFUser', null=True, blank=True)
    timestamp = models.DateTimeField()
    send_type = models.CharField(max_length=50, db_index=True, validators=[validate_subscription_type, ])
    event = models.CharField(max_length=50)
    message = models.CharField(max_length=2048)
    # TODO: Could this be a m2m with or without an order field?
    node_lineage = ArrayField(models.CharField(max_length=5))
