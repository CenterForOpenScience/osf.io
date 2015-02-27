from modularodm import fields
from framework.mongo import StoredObject, ObjectId
from website.notifications.constants import NOTIFICATION_TYPES


class Subscription(StoredObject):
    _id = fields.StringField(primary=True)  # pxyz_wiki_updated, uabc_comment_replies

    event_name = fields.StringField()      # wiki_updated, comment_replies
    owner = fields.AbstractForeignField()

    # Notification types
    none = fields.ForeignField('user', list=True, backref='none')
    email_digest = fields.ForeignField('user', list=True, backref='email_digest')
    email_transactional = fields.ForeignField('user', list=True, backref='email_transactional')

    def remove_user_from_subscription(self, user):
        for n in NOTIFICATION_TYPES:
            if user in getattr(self, n):
                getattr(self, n).remove(user)
                self.save()


class DigestNotification(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    user_id = fields.StringField()
    timestamp = fields.DateTimeField()
    event = fields.StringField()
    message = fields.StringField()
    node_lineage = fields.StringField(list=True)
