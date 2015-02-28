from modularodm import fields

from framework.mongo import StoredObject, ObjectId

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

    def remove_user_from_subscription(self, user, save=True):
        for notification_type in NOTIFICATION_TYPES:
            try:
                getattr(self, notification_type, []).remove(user)
            except ValueError:
                pass

        if isinstance(self.owner, Node):
            parent = self.owner.parent or self.owner

            try:
                parent.child_node_subscriptions[user._id].remove(self.owner._id)
                parent.save()
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
