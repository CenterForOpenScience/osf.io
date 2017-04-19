from modularodm import fields

from framework.mongo import StoredObject, ObjectId
from modularodm.exceptions import ValidationValueError

from website.project.model import Node
from website.notifications.constants import NOTIFICATION_TYPES, NODE_SUBSCRIPTIONS_AVAILABLE, USER_SUBSCRIPTIONS_AVAILABLE
import re


def validate_subscription_type(value):
    if value not in NOTIFICATION_TYPES:
        raise ValidationValueError


def validate_event_type(value):
    """

    :param value:

    Checks if the value passed in is in the NODE_SUBSCRIPTIONS_AVAILABLE or USER_SUBSCRIPTIONS_AVAILABLE
    if it is an event name.  Since the only things from NODE_SUBSCRIPTIONS_AVAILABLE that contains "file_updated"
    is preceded by a user ID, a regex checker was added for that.
    """
    prefix = re.compile('[[a-zA-Z0-9]*_]?')
    if prefix.search(value):
        value = 'file_updated'
    if value not in NODE_SUBSCRIPTIONS_AVAILABLE and value not in USER_SUBSCRIPTIONS_AVAILABLE:
        raise ValidationValueError


class NotificationSubscription(StoredObject):
    _id = fields.StringField(primary=True)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = fields.StringField(index=True, validate=validate_event_type)      # wiki_updated, comment_replies
    owner = fields.AbstractForeignField()

    # Notification types
    none = fields.ForeignField('user', list=True)
    email_digest = fields.ForeignField('user', list=True)
    email_transactional = fields.ForeignField('user', list=True)

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


class NotificationDigest(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    user_id = fields.StringField(index=True)
    timestamp = fields.DateTimeField()
    send_type = fields.StringField(index=True, validate=validate_subscription_type)
    event = fields.StringField(index=True, validate=validate_event_type)
    message = fields.StringField()
    node_lineage = fields.StringField(list=True)
