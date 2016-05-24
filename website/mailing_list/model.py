# -*- coding: utf-8 -*-
import datetime

from modularodm import fields, StoredObject

from framework.mongo import ObjectId

class MailingListEventLog(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    date_created = fields.DateTimeField(default=datetime.datetime.utcnow)

    email_content = fields.StringField()
    sending_user = fields.ForeignField('user')
    destination_node = fields.ForeignField('node')
