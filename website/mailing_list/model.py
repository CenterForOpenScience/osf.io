# -*- coding: utf-8 -*-
import datetime

from modularodm import fields, StoredObject

from framework.mongo import ObjectId
from framework.mongo.utils import unique_on

@unique_on(['destination_node', '_id'])
class MailingListEventLog(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    date_created = fields.DateTimeField(default=datetime.datetime.utcnow, index=True)

    email_content = fields.StringField()
    sending_user = fields.ForeignField('user', index=True)
    destination_node = fields.ForeignField('node', index=True)
