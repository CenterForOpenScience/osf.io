import mandrill
import bson
from datetime import datetime, timedelta
from modularodm import fields, Q
from framework.mongo import StoredObject
import website.mails.mail_types as wm

def _send_email(to_address, template, data):
    '''
    Dependent on what is used to send the email
    :return: bool on success
    '''
    try:
        mandrill_client = mandrill.Mandrill('change-me')
        message = {
            'html': '<h1> This is a mandrill email </h1>',
            'subject': data.get('subject') if data else 'Welp',
            'from_email': 'h.moco@hotmail.com',
            'to': [{
                'email': str(to_address)
                }]
            }

        mandrill_client.messages.send_template(template_name=template, template_content=data.get('template_content') if data else [], message=message, async=False)
        # Log result
        return True
    except mandrill.Error, e:
        return False

class QueuedEmail(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    to_ = fields.ForeignField('User')
    send_at = fields.DateTimeField(default=None)
    email_type = fields.StringField(default=None)
    data = fields.DictionaryField(default=None)

    def create(self, to_user, email_type, send_at, data=None):
        self.to_ = to_user
        self.email_type = email_type
        self.send_at = send_at
        self.data = data
        self.save()

    def send_email(self):
        emailType = wm.email_types[self.email_type]
        if emailType['callback'](self) and self.to_.mailing_lists.get('help'):
            if _send_email(to_address=self.to_.username, template=emailType['template'], data=self.data):
                sent = SentEmail()
                sent.email_type = self.email_type
                sent.sent_to = self.to_
                sent.sent_at = datetime.now()
                sent.save()
                self.__class__.remove_one(self)
        else:
            self.__class__.remove_one(self)

    def delete(self):
        self.__class__.remove_one(self)

    def find_others_to(self):
        return list(SentEmail.find(Q('sent_to', 'eq', self.to_)))

class SentEmail(StoredObject):
    _id = fields.StringField(primary=True)
    sent_to = fields.ForeignField('User')
    sent_at = fields.DateTimeField(default=None)
    email_type = fields.StringField(default=None)

