# -*- coding: utf-8 -*-
import datetime

from modularodm import fields, StoredObject

from framework.mongo import ObjectId
from framework.mongo.utils import unique_on

@unique_on(['destination_node', '_id'])
class MailingListEventLog(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    date_created = fields.DateTimeField(default=datetime.datetime.utcnow, index=True)

    content = fields.StringField()
    sending_email = fields.StringField(index=True)
    sending_user = fields.ForeignField('user', index=True)
    destination_node = fields.ForeignField('node', index=True)
    intended_recipients = fields.ForeignField('user', list=True)
    status = fields.StringField()

    # Possible statuses
    UNAUTHORIZED = 'no_user'
    NOT_FOUND = 'node_dne'
    DELETED = 'node_deleted'
    FORBIDDEN = 'no_access'
    DISABLED = 'mailing_list_disabled'
    NO_RECIPIENTS = 'no_recipients'
    BOUNCED = 'bounced'
    AUTOREPLY = 'auto_reply'
    OK = 'sent'
