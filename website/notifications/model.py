from modularodm import fields

from framework.mongo import StoredObject, ObjectId

from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import datetime
from furl import furl

from website.project.model import Node
from website.notifications.constants import NOTIFICATION_TYPES


class NotificationSubscription(StoredObject):
    _id = fields.StringField(primary=True)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = fields.StringField()      # wiki_updated, comment_replies
    owner = fields.AbstractForeignField()

    # Notification types
    none = fields.ForeignField('user', list=True, backref='none')
    email_digest = fields.ForeignField('user', list=True, backref='email_digest')
    email_transactional = fields.ForeignField('user', list=True, backref='email_transactional')

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
    user_id = fields.StringField()
    timestamp = fields.DateTimeField()
    event = fields.StringField()
    message = fields.StringField()
    node_lineage = fields.StringField(list=True)


class BaseNotification:
    """Base notification class for building notification events and messages"""
    __metaclass__ = ABCMeta

    def __init__(self, user, node, event):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.node_id = node._id
        self.event = event
        self.timestamp = datetime.utcnow()

    @abstractmethod
    def perform(self):
        """Send the notifications"""
        pass

    @abstractmethod
    def form_message(self):
        """Piece together the message to be sent to subscribed users"""
        pass

    @abstractmethod
    def form_event(self):
        """
        Use NODE_SUBSCRIPTIONS_AVAILABLE and USER_SUBSCRIPTIONS_AVAILABLE plus UIDs
        where available to denote individual subscriptions.
        """
        pass

    @abstractmethod
    def form_url(self):
        """Build url from relevant info"""
        return "Nada"
