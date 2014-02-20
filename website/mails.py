# -*- coding: utf-8 -*-
import os
import logging

from mako.lookup import TemplateLookup

from framework.email.tasks import send_email as framework_send_email
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
        self.subject = subject

    def html(self, **context):
        """Render the HTML email message."""
        tpl_name = self.tpl_prefix + HTML_EXT
        return render_message(tpl_name, **context)

    def text(self, **context):
        """Render the plaintext email message"""
        tpl_name = self.tpl_prefix + TXT_EXT
        return render_message(tpl_name, **context)


def render_message(tpl_name, **context):
    """Render an email message."""
    tpl = _tpl_lookup.get_template(tpl_name)
    return tpl.render(**context)


def send_mail(to_addr, mail, mimetype='plain', **context):
    """Send an email from the OSF.
    Example: ::

        from website import mails

        mails.send_email('foo@bar.com', mails.TEST, name="Foo")

    :param str to_addr: The recipient's email address
    :param Mail mail: The mail object
    :param str mimetype: Either 'plain' or 'html'
    :param **context: Context vars for the message template

    .. note:
         Requires celery worker.

    """
    subject = mail.subject
    message = mail.text(**context) if mimetype == 'plain' else mail.html(**context)
    # Don't use ttls and login in DEV_MODE
    ttls = login = not settings.DEV_MODE
    logger.debug('Sending email...')
    logger.debug('To: {to_addr}\nSubject: {subject}\nMessage: {message}'.format(**locals()))
    return framework_send_email.delay(
        from_addr=settings.FROM_EMAIL,
        to_addr=to_addr,
        subject=mail.subject,
        message=message,
        mimetype=mimetype,
        ttls=ttls, login=login
    )

# The Emails

TEST = Mail(name='test', subject='A test email')
