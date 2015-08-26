import mandrill
from datetime import datetime, timedelta
from modularodm import fields, Q
from framework.mongo import StoredObject

def send_email(to_address, template, data):
    '''
    Dependent on what is used to send the email
    :return: bool on success
    '''
    try:
        mandrill_client = mandrill.Mandrill('Change_me')
        message = {
            'html': '<h1> This is a mandrill email </h1>',
            'subject': data.get('subject'),
            'from_email': 'osf.io',
            'to': [{
                'email': to_address
                }]
            }

        result = mandrill_client.messages.send_template(template_name=template, template_content=data.get('template_content'), message=message, async=False)
        # Log result
        return True
    except mandrill.Error, e:
        return False

class QueuedEmail(StoredObject):
    _id = fields.StringField(primary=True)
    to_ = fields.ForeignField('User')
    send_at = fields.DatetimeField(default=None)
    email_type = fields.StringField(default=None)
    data = fields.DictionaryField(default=None)
    sent = fields.BooleanField(default=False)

    def __init__(self, to_user, email_type, send_at=None, data=None):
        self.to_ = to_user
        self.email_type = email_types[email_type]
        self.send_at = send_at or datetime.now()
        self.data = data
        self.save()

    def send_email(self):
        if self.email_type['callback'](self):
            send_email(to_address=self.to_.email, template=self.email_type['template'], data=self.data)
            sent = SentEmail()
            sent.email_type = self.email_type
            sent.sent_to = self._to
            sent.sent_at = datetime.now()
            sent.save()
        self.sent = True
        self.save()
        self.__class__.remove_one(self)

class SentEmail(StoredObject):
    sent_to = fields.ForeignField('User')
    sent_at = fields.DatetimeField()
    email_type = fields.ForeignField('Email')

def week_check(email):
    sent_emails = list(SentEmail.find(Q('sent_to', 'eq', email.to_)))
    for email in sent_emails:
        if email.sent_at > (datetime.utcnow() - timedelta(weeks=1)) :
            return False
    return True

def no_addon(email):
    if week_check(email):
        if len(email.to_.get_addons()) is 0:
            return True
    return False

email_types = {
    'no_addon': {
        'template': 'no_addon',
        'callback': no_addon
    },
}
