from datetime import datetime

import pytz
from django.contrib.postgres.fields import ArrayField
from django.db import models
from osf.models import Node
from osf.models import OSFUser
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.validators import validate_subscription_type
from osf.utils.fields import NonNaiveDateTimeField
from website.notifications.constants import NOTIFICATION_TYPES


class NotificationSubscription(BaseModel):
    primary_identifier_name = '_id'
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.notifications.model.NotificationSubscription'
    modm_query = None
    migration_page_size = 20000
    # /TODO DELETE ME POST MIGRATION
    _id = models.CharField(max_length=50, db_index=True)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = models.CharField(max_length=50)  # wiki_updated, comment_replies

    user = models.ForeignKey('OSFUser', null=True, related_name='notification_subscriptions', blank=True)
    node = models.ForeignKey('Node', null=True, blank=True, related_name='notification_subscriptions')

    # Notification types
    none = models.ManyToManyField('OSFUser', related_name='+')  # reverse relationships
    email_digest = models.ManyToManyField('OSFUser', related_name='+')  # for these
    email_transactional = models.ManyToManyField('OSFUser', related_name='+')  # are pointless

    @classmethod
    def load(cls, q):
        # modm doesn't throw exceptions when loading things that don't exist
        try:
            return cls.objects.get(_id=q)
        except cls.DoesNotExist:
            return None

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        """
        Given a modm object, make a django object with the same local fields.
        This is a base method that may work for simple things. It should be customized for complex ones.
        :param modm_obj:
        :return:
        """

        django_obj = cls()
        django_obj._id = modm_obj._id

        local_django_fields = set([x.name for x in django_obj._meta.get_fields() if not x.is_relation])

        intersecting_fields = set(modm_obj.to_storage().keys()).intersection(
            set(local_django_fields))

        for field in intersecting_fields:
            modm_value = getattr(modm_obj, field)
            if modm_value is None:
                continue
            if isinstance(modm_value, datetime):
                modm_value = pytz.utc.localize(modm_value)
            setattr(django_obj, field, modm_value)

        return django_obj

    @property
    def owner(self):
        # ~100k have owner==user
        if self.user is not None:
            return self.user
        # ~8k have owner=Node
        elif self.node is not None:
            return self.node

    @owner.setter
    def owner(self, value):
        if isinstance(value, OSFUser):
            self.user = value
        elif isinstance(value, Node):
            self.node = value

    def add_user_to_subscription(self, user, notification_type, save=True):
        for nt in NOTIFICATION_TYPES:
            if getattr(self, nt).filter(id=user.id).exists():
                if nt != notification_type:
                    getattr(self, nt).remove(user)
            else:
                if nt == notification_type:
                    getattr(self, nt).add(user)

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
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.notifications.model.NotificationDigest'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    user = models.ForeignKey('OSFUser', null=True, blank=True)
    timestamp = NonNaiveDateTimeField()
    send_type = models.CharField(max_length=50, db_index=True, validators=[validate_subscription_type, ])
    event = models.CharField(max_length=50)
    message = models.CharField(max_length=2048)
    # TODO: Could this be a m2m with or without an order field?
    node_lineage = ArrayField(models.CharField(max_length=5))
