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
import logging

from mako.lookup import TemplateLookup, Template
from framework.email import tasks
from website import settings


logger = logging.getLogger(__name__)

EMAIL_TEMPLATES_DIR = os.path.join(settings.TEMPLATES_PATH, 'emails')

_tpl_lookup = TemplateLookup(
    directories=[EMAIL_TEMPLATES_DIR]
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
        mail_server=mail_server)

    if settings.USE_CELERY:
        return mailer.apply_async(kwargs=kwargs, link=callback)
    else:
        ret = mailer(**kwargs)
        if callback:
            callback()

        return ret

# Predefined Emails

TEST = Mail('test', subject='A test email to ${name}')
CONFIRM_EMAIL = Mail('confirm', subject='Confirm your email address')
INVITE = Mail('invite', subject='You have been added as a contributor to an OSF project.')

FORWARD_INVITE = Mail('forward_invite', subject='Please forward to ${fullname}')
FORWARD_INVITE_REGiSTERED = Mail('forward_invite_registered', subject='Please forward to ${fullname}')

FORGOT_PASSWORD = Mail('forgot_password', subject='Reset Password')
PENDING_VERIFICATION = Mail('pending_invite', subject="Your account is almost ready!")
PENDING_VERIFICATION_REGISTERED = Mail('pending_registered', subject='Received request to be a contributor')

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

DIGEST = Mail('digest', subject='OSF Email Digest')
TRANSACTIONAL = Mail('transactional', subject='OSF: ${subject}')
