from modularodm import fields
from framework.mongo import StoredObject


class Subscription(StoredObject):
    _id = fields.StringField(primary=True) # pxyz_wiki_updated, uabc_comment_replies
    node_id = fields.StringField()     # xyz
    event_name = fields.StringField()      # wiki_updated

    # Notification types
    email_transactional = fields.ForeignField('user', list=True, backref='email_transactional')
