import bson
from datetime import datetime

from modularodm import fields, Q
from framework.mongo import StoredObject
from .mails import Mail, send_mail
from website import settings
from website.mails import presends


class QueuedMail(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    user = fields.ForeignField('User', index=True, required=True)
    to_addr = fields.StringField()
    send_at = fields.DateTimeField(index=True, required=True)

    # string denoting the template, presend to be used. Has to be an index of queue_mail types
    email_type = fields.StringField(index=True, required=True)

    # dictionary with variables used to populate mako template and store information used in presends
    # Example:
    # self.data = {
    #    'nid' : 'ShIpTo',
    #    'fullname': 'Florence Welch',
    #}
    data = fields.DictionaryField()
    sent_at = fields.DateTimeField(index=True)

    def send_mail(self):
        """
        Grabs the data from this email, checks for user subscription to help mails,

        constructs the mail object and checks presend. Then attempts to send the email
        through send_mail()
        :return: boolean based on whether email was sent.
        """
        mail_struct = queue_mail_types[self.email_type]
        presend = mail_struct['presend'](self)
        mail = Mail(
            mail_struct['template'],
            subject=mail_struct['subject'],
            categories=mail_struct.get('categories', None)
        )
        self.data['osf_url'] = settings.DOMAIN
        if presend and self.user.is_active and self.user.osf_mailing_lists.get(settings.OSF_HELP_LIST):
            send_mail(self.to_addr or self.user.username, mail, mimetype='html', **(self.data or {}))
            self.sent_at = datetime.utcnow()
            self.save()
            return True
        else:
            self.__class__.remove_one(self)
            return False

    def find_sent_of_same_type_and_user(self):
        """
        Queries up for all emails of the same type as self, sent to the same user as self.
        Does not look for queue-up emails.
        :return: a list of those emails
        """
        return self.__class__.find(
            Q('email_type', 'eq', self.email_type) &
            Q('user', 'eq', self.user) &
            Q('sent_at', 'ne', None)
        )

def queue_mail(to_addr, mail, send_at, user, **context):
    """
    Queue an email to be sent using send_mail after a specified amount
    of time and if the presend returns True. The presend is attached to
    the template under mail.

    :param to_addr: the address email is to be sent to
    :param mail:  the type of mail. Struct following template:
                        { 'presend': function(),
                            'template': mako template name,
                            'subject': mail subject }
    :param send_at: datetime object of when to send mail
    :param user: user object attached to mail
    :param context: IMPORTANT kwargs to be attached to template.
                    Sending mail will fail if needed for template kwargs are
                    not parameters.
    :return: the QueuedMail object created
    """
    new_mail = QueuedMail(
        user=user,
        to_addr=to_addr,
        send_at=send_at,
        email_type=mail['template'],
        data=context
    )
    new_mail.save()
    return new_mail


# Predefined email templates. Structure:
#EMAIL_TYPE = {
#    'template': the mako template used for email_type,
#    'subject': subject used for the actual email,
#    'categories': categories to attach to the email using Sendgrid's SMTPAPI.
#    'presend': predicate function that determines whether an email should be sent. May also
#               modify mail.data.
#}

NO_ADDON = {
    'template': 'no_addon',
    'subject': 'Link an add-on to your OSF project',
    'presend': presends.no_addon,
    'categories': ['engagement', 'engagement-no-addon']
}

NO_LOGIN = {
    'template': 'no_login',
    'subject': 'What you\'re missing on the OSF',
    'presend': presends.no_login,
    'categories': ['engagement', 'engagement-no-login']
}

NEW_PUBLIC_PROJECT = {
    'template': 'new_public_project',
    'subject': 'Now, public. Next, impact.',
    'presend': presends.new_public_project,
    'categories': ['engagement', 'engagement-new-public-project']
}

WELCOME_OSF4M = {
    'template': 'welcome_osf4m',
    'subject': 'The benefits of sharing your presentation',
    'presend': presends.welcome_osf4m,
    'categories': ['engagement', 'engagement-welcome-osf4m']
}

NO_ADDON_TYPE = 'no_addon'
NO_LOGIN_TYPE = 'no_login'
NEW_PUBLIC_PROJECT_TYPE = 'new_public_project'
WELCOME_OSF4M_TYPE = 'welcome_osf4m'

# Used to keep relationship from stored string 'email_type' to the predefined queued_email objects.
queue_mail_types = {
    NO_ADDON_TYPE: NO_ADDON,
    NO_LOGIN_TYPE: NO_LOGIN,
    NEW_PUBLIC_PROJECT_TYPE: NEW_PUBLIC_PROJECT,
    WELCOME_OSF4M_TYPE: WELCOME_OSF4M
}
