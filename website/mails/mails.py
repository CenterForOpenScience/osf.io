# -*- coding: utf-8 -*-
"""OSF mailing utilities.

Email templates go in website/templates/emails
Templates must end in ``.txt.mako`` for plaintext emails or``.html.mako`` for html emails.

You can then create a `Mail` object given the basename of the template and
the email subject. ::

    CONFIRM_EMAIL = Mail(tpl_prefix='confirm', subject="Confirm your email address")

You can then use ``send_mail`` to send the email.

Usage: ::

    from website import mails
    ...
    mails.send_mail('foo@bar.com', mails.CONFIRM_EMAIL, user=user)

"""
import os
import bson
import logging
from datetime import datetime

from mako.lookup import TemplateLookup, Template

from modularodm import fields, Q
from framework.email import tasks
from framework.mongo import StoredObject
from website import settings
from website.mails import mail_callbacks

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES_DIR = os.path.join(settings.TEMPLATES_PATH, 'emails')

_tpl_lookup = TemplateLookup(
    directories=[EMAIL_TEMPLATES_DIR],
)

TXT_EXT = '.txt.mako'
HTML_EXT = '.html.mako'


class Mail(object):
    """An email object.

    :param str tpl_prefix: The template name prefix.
    :param str subject: The subject of the email.
    """

    def __init__(self, tpl_prefix, subject):
        self.tpl_prefix = tpl_prefix
        self._subject = subject

    def html(self, **context):
        """Render the HTML email message."""
        tpl_name = self.tpl_prefix + HTML_EXT
        return render_message(tpl_name, **context)

    def text(self, **context):
        """Render the plaintext email message"""
        tpl_name = self.tpl_prefix + TXT_EXT
        return render_message(tpl_name, **context)

    def subject(self, **context):
        return Template(self._subject).render(**context)


def render_message(tpl_name, **context):
    """Render an email message."""
    tpl = _tpl_lookup.get_template(tpl_name)
    return tpl.render(**context)


def send_mail(to_addr, mail, mimetype='plain', from_addr=None, mailer=None,
            username=None, password=None, mail_server=None, callback=None, **context):
    """Send an email from the OSF.
    Example: ::

        from website import mails

        mails.send_email('foo@bar.com', mails.TEST, name="Foo")

    :param str to_addr: The recipient's email address
    :param Mail mail: The mail object
    :param str mimetype: Either 'plain' or 'html'
    :param function callback: celery task to execute after send_mail completes
    :param **context: Context vars for the message template

    .. note:
         Uses celery if available
    """

    from_addr = from_addr or settings.FROM_EMAIL
    mailer = mailer or tasks.send_email
    subject = mail.subject(**context)
    message = mail.text(**context) if mimetype in ('plain', 'txt') else mail.html(**context)
    # Don't use ttls and login in DEBUG_MODE
    ttls = login = not settings.DEBUG_MODE
    logger.debug('Sending email...')
    logger.debug(u'To: {to_addr}\nFrom: {from_addr}\nSubject: {subject}\nMessage: {message}'.format(**locals()))

    kwargs = dict(
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        message=message,
        mimetype=mimetype,
        ttls=ttls,
        login=login,
        username=username,
        password=password,
        mail_server=mail_server
    )

    if settings.USE_CELERY:
        return mailer.apply_async(kwargs=kwargs, link=callback)
    else:
        ret = mailer(**kwargs)
        if callback:
            callback()

        return ret

def queue_mail(to_addr, mail, send_at, user, **context):
    """
    Queue an email to be sent using send_mail after a specified amount
    of time and if the callback returns True. The callback is attached to
    the template under mail.

    :param to_addr: the address email is to be sent to
    :param mail:  the type of mail. Struct following template:
                        { 'callback': function(),
                            'template': mako template name,
                            'subject': mail subject }
    :param send_at: datetime object of when to send mail
    :param user: user object attached to mail
    :param context: IMPORTANT kwargs to be attached to template.
                    Sending mail will fail if wrong all kwargs are
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

class QueuedMail(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    user = fields.ForeignField('User')
    to_addr = fields.StringField()
    send_at = fields.DateTimeField()
    email_type = fields.StringField()
    data = fields.DictionaryField()
    sent_at = fields.DateTimeField(index=True)

    def send_mail(self):
        """
        Grabs the data from this email, checks for user subscription to help mails,

        constructs the mail object and checks callback. Then attempts to send the email
        through send_mail()
        :return: boolean based on whether email was sent.
        """
        mail_struct = queue_mail_types[self.email_type]
        callback = mail_struct['callback'](self)
        mail = Mail(
            mail_struct['template'],
            subject=mail_struct['subject']
        )
        self.data['osf_url'] = settings.DOMAIN
        if callback and self.user.osf_mailing_lists.get(settings.OSF_HELP_LIST):
            send_mail(self.to_addr, mail, mimetype='html', **(self.data or {}))
            self.sent_at = datetime.utcnow()
            self.save()
            return True
        else:
            self.__class__.remove_one(self)
            return False

    def find_same_email_sent_to_same_user(self):
        """
        Queries up for all emails of the same type as self, sent to the same user as self.
        Does not look for queue-up emails.
        :return: a list of those emails
        """
        return list(self.__class__.find(
            Q('email_type', 'eq', self.email_type) &
            Q('user', 'eq', self.user) &
            Q('sent_at', 'ne', None)
        ))

# Predefined Emails

TEST = Mail('test', subject='A test email to ${name}')

CONFIRM_EMAIL = Mail('confirm', subject='Open Science Framework Account Verification')
CONFIRM_MERGE = Mail('confirm_merge', subject='Confirm account merge')

REMOVED_EMAIL = Mail('email_removed', subject='Email address removed from your OSF account')
PRIMARY_EMAIL_CHANGED = Mail('primary_email_changed', subject='Primary email changed')
INVITE = Mail('invite', subject='You have been added as a contributor to an OSF project.')
CONTRIBUTOR_ADDED = Mail('contributor_added', subject='You have been added as a contributor to an OSF project.')

FORWARD_INVITE = Mail('forward_invite', subject='Please forward to ${fullname}')
FORWARD_INVITE_REGISTERED = Mail('forward_invite_registered', subject='Please forward to ${fullname}')

FORGOT_PASSWORD = Mail('forgot_password', subject='Reset Password')
PENDING_VERIFICATION = Mail('pending_invite', subject="Your account is almost ready!")
PENDING_VERIFICATION_REGISTERED = Mail('pending_registered', subject='Received request to be a contributor')

REQUEST_EXPORT = Mail('support_request', subject='[via OSF] Export Request')
REQUEST_DEACTIVATION = Mail('support_request', subject='[via OSF] Deactivation Request')

CONFERENCE_SUBMITTED = Mail(
    'conference_submitted',
    subject='Project created on Open Science Framework',
)
CONFERENCE_INACTIVE = Mail(
    'conference_inactive',
    subject='Open Science Framework Error: Conference inactive',
)
CONFERENCE_FAILED = Mail(
    'conference_failed',
    subject='Open Science Framework Error: No files attached',
)

DIGEST = Mail('digest', subject='OSF Notifications')
TRANSACTIONAL = Mail('transactional', subject='OSF: ${subject}')

# Retraction related Mail objects
PENDING_RETRACTION_ADMIN = Mail(
    'pending_retraction_admin',
    subject='Retraction pending for one of your projects.'
)
PENDING_RETRACTION_NON_ADMIN = Mail(
    'pending_retraction_non_admin',
    subject='Retraction pending for one of your projects.'
)
# Embargo related Mail objects
PENDING_EMBARGO_ADMIN = Mail(
    'pending_embargo_admin',
    subject='Registration pending for one of your projects.'
)
PENDING_EMBARGO_NON_ADMIN = Mail(
    'pending_embargo_non_admin',
    subject='Registration pending for one of your projects.'
)
# Registration related Mail Objects
PENDING_REGISTRATION_ADMIN = Mail(
    'pending_registration_admin',
    subject='Registration pending for one of your projects.'
)
PENDING_REGISTRATION_NON_ADMIN = Mail(
    'pending_registration_non_admin',
    subject='Registration pending for one of your projects.'
)
FILE_OPERATION_SUCCESS = Mail(
    'file_operation_success',
    subject='Your ${action} has finished',
)

FILE_OPERATION_FAILED = Mail(
    'file_operation_failed',
    subject='Your ${action} has failed',
)

UNESCAPE = "<% from website.util.sanitize import unescape_entities %> ${unescape_entities(src.title)}"
PROBLEM_REGISTERING = "Problem registering " + UNESCAPE

ARCHIVE_SIZE_EXCEEDED_DESK = Mail(
    'archive_size_exceeded_desk',
    subject=PROBLEM_REGISTERING
)
ARCHIVE_SIZE_EXCEEDED_USER = Mail(
    'archive_size_exceeded_user',
    subject=PROBLEM_REGISTERING
)

ARCHIVE_COPY_ERROR_DESK = Mail(
    'archive_copy_error_desk',
    subject=PROBLEM_REGISTERING
)
ARCHIVE_COPY_ERROR_USER = Mail(
    'archive_copy_error_user',
    subject=PROBLEM_REGISTERING
)

ARCHIVE_UNCAUGHT_ERROR_DESK = Mail(
    'archive_uncaught_error_desk',
    subject=PROBLEM_REGISTERING
)
ARCHIVE_UNCAUGHT_ERROR_USER = Mail(
    'archive_uncaught_error_user',
    subject=PROBLEM_REGISTERING
)

ARCHIVE_SUCCESS = Mail(
    'archive_success',
    subject="Registration of " + UNESCAPE + " complete"
)


WELCOME = Mail(
    'welcome',
    subject='Welcome to the Open Science Framework'
)

# Predefined emails with callbacks
NO_ADDON = {
    'template': 'no_addon',
    'subject': 'Link an add-on to your OSF project',
    'callback': mail_callbacks.no_addon
}

NO_LOGIN = {
    'template': 'no_login',
    'subject': 'What you\'re missing on the OSF',
    'callback': mail_callbacks.no_login
}

NEW_PUBLIC_PROJECT = {
    'template': 'new_public_project',
    'subject': 'Now, public. Next, impact.',
    'callback': mail_callbacks.new_public_project
}

WELCOME_OSF4M = {
    'template': 'welcome_osf4m',
    'subject': 'The benefits of sharing your presentation',
    'callback': mail_callbacks.welcome_osf4m
}

queue_mail_types = {
    'no_addon': NO_ADDON,
    'no_login': NO_LOGIN,
    'new_public_project': NEW_PUBLIC_PROJECT,
    'welcome_osf4m': WELCOME_OSF4M
}
