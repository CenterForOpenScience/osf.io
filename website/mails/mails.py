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
    directories=[EMAIL_TEMPLATES_DIR],
)

TXT_EXT = '.txt.mako'
HTML_EXT = '.html.mako'


class Mail(object):
    """An email object.

    :param str tpl_prefix: The template name prefix.
    :param str subject: The subject of the email.
    :param iterable categories: Categories to add to the email using SendGrid's
        SMTPAPI. Used for email analytics.
        See https://sendgrid.com/docs/User_Guide/Statistics/categories.html
    """

    def __init__(self, tpl_prefix, subject, categories=None):
        self.tpl_prefix = tpl_prefix
        self._subject = subject
        self.categories = categories

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


def send_mail(to_addr, mail, mimetype='plain', from_addr=None, mailer=None, celery=True,
            username=None, password=None, callback=None, attachment_name=None, attachment_content=None, **context):
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
        categories=mail.categories,
        attachment_name=attachment_name,
        attachment_content=attachment_content,
    )

    logger.debug('Preparing to send...')
    if settings.USE_EMAIL:
        if settings.USE_CELERY and celery:
            logger.debug('Sending via celery...')
            return mailer.apply_async(kwargs=kwargs, link=callback)
        else:
            logger.debug('Sending without celery')
            ret = mailer(**kwargs)
            if callback:
                callback()

            return ret


def get_english_article(word):
    """
    Decide whether to use 'a' or 'an' for a given English word.

    :param word: the word immediately after the article
    :return: 'a' or 'an'
    """
    return 'a' + ('n' if word[0].lower() in 'aeiou' else '')


# Predefined Emails

TEST = Mail('test', subject='A test email to ${name}', categories=['test'])

# Emails for first-time login through external identity providers.
EXTERNAL_LOGIN_CONFIRM_EMAIL_CREATE = Mail(
    'external_confirm_create',
    subject='Open Science Framework Account Verification'
)

FORK_COMPLETED = Mail(
    'fork_completed',
    subject='Your fork has completed'
)

FORK_FAILED = Mail(
    'fork_failed',
    subject='Your fork has failed'
)

EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK = Mail(
    'external_confirm_link',
    subject='Open Science Framework Account Verification'
)
EXTERNAL_LOGIN_LINK_SUCCESS = Mail(
    'external_confirm_success',
    subject='Open Science Framework Account Verification Success'
)

# Sign up confirmation emails for OSF, native campaigns and branded campaigns
INITIAL_CONFIRM_EMAIL = Mail(
    'initial_confirm',
    subject='Open Science Framework Account Verification'
)
CONFIRM_EMAIL = Mail(
    'confirm',
    subject='Add a new email to your OSF account'
)
CONFIRM_EMAIL_PREREG = Mail(
    'confirm_prereg',
    subject='Open Science Framework Account Verification, Preregistration Challenge'
)
CONFIRM_EMAIL_ERPC = Mail(
    'confirm_erpc',
    subject='Open Science Framework Account Verification, Election Research Preacceptance Competition'
)
CONFIRM_EMAIL_PREPRINTS = lambda name, provider: Mail(
    'confirm_preprints_{}'.format(name),
    subject='Open Science Framework Account Verification, {}'.format(provider)
)
CONFIRM_EMAIL_REGISTRIES_OSF = Mail(
    'confirm_registries_osf',
    subject='Open Science Framework Account Verification, OSF Registries'
)
CONFIRM_EMAIL_MODERATION = lambda provider: Mail(
    'confirm_moderation',
    subject='Open Science Framework Account Verification, {}'.format(provider.name)
)

# Merge account, add or remove email confirmation emails.
CONFIRM_MERGE = Mail('confirm_merge', subject='Confirm account merge')
REMOVED_EMAIL = Mail('email_removed', subject='Email address removed from your OSF account')
PRIMARY_EMAIL_CHANGED = Mail('primary_email_changed', subject='Primary email changed')


# Contributor added confirmation emails
INVITE_DEFAULT = Mail(
    'invite_default',
    subject='You have been added as a contributor to an OSF project.'
)
INVITE_PREPRINT = lambda template, provider: Mail(
    'invite_preprints_{}'.format(template),
    subject='You have been added as a contributor to {} {} {}.'.format(get_english_article(provider.name), provider.name, provider.preprint_word)
)
CONTRIBUTOR_ADDED_DEFAULT = Mail(
    'contributor_added_default',
    subject='You have been added as a contributor to an OSF project.'
)
CONTRIBUTOR_ADDED_PREPRINT = lambda template, provider: Mail(
    'contributor_added_preprints_{}'.format(template),
    subject='You have been added as a contributor to {} {} {}.'.format(get_english_article(provider.name), provider.name, provider.preprint_word)
)
CONTRIBUTOR_ADDED_PREPRINT_NODE_FROM_OSF = Mail(
    'contributor_added_preprint_node_from_osf',
    subject='You have been added as a contributor to an OSF project.'
)
MODERATOR_ADDED = lambda provider: Mail(
    'moderator_added',
    subject='You have been added as a moderator for {}'.format(provider.name)
)
CONTRIBUTOR_ADDED_ACCESS_REQUEST = Mail(
    'contributor_added_access_request',
    subject='Your access request to an OSF project has been approved.'
)
PREPRINT_CONFIRMATION_DEFAULT = Mail(
    'preprint_confirmation_default',
    subject="You've shared a preprint on OSF preprints"
)
PREPRINT_CONFIRMATION_BRANDED = lambda provider: Mail(
    'preprint_confirmation_branded',
    subject="You've shared {} {} on {}".format(
        get_english_article(provider.preprint_word),
        provider.preprint_word, provider.name
    )
)
FORWARD_INVITE = Mail('forward_invite', subject='Please forward to ${fullname}')
FORWARD_INVITE_REGISTERED = Mail('forward_invite_registered', subject='Please forward to ${fullname}')

FORGOT_PASSWORD = Mail('forgot_password', subject='Reset Password')
PASSWORD_RESET = Mail('password_reset', subject='Your OSF password has been reset')
PENDING_VERIFICATION = Mail('pending_invite', subject='Your account is almost ready!')
PENDING_VERIFICATION_REGISTERED = Mail('pending_registered', subject='Received request to be a contributor')

REQUEST_EXPORT = Mail('support_request', subject='[via OSF] Export Request')
REQUEST_DEACTIVATION = Mail('support_request', subject='[via OSF] Deactivation Request')

SPAM_USER_BANNED = Mail('spam_user_banned', subject='[OSF] Account flagged as spam')

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

DIGEST = Mail(
    'digest', subject='OSF Notifications',
    categories=['notifications', 'notifications-digest']
)
TRANSACTIONAL = Mail(
    'transactional', subject='OSF: ${subject}',
    categories=['notifications', 'notifications-transactional']
)

# Retraction related Mail objects
PENDING_RETRACTION_ADMIN = Mail(
    'pending_retraction_admin',
    subject='Withdrawal pending for one of your projects.'
)
PENDING_RETRACTION_NON_ADMIN = Mail(
    'pending_retraction_non_admin',
    subject='Withdrawal pending for one of your projects.'
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
PENDING_EMBARGO_TERMINATION_ADMIN = Mail(
    'pending_embargo_termination_admin',
    subject='Request to end an embargo early for one of your projects.'
)
PENDING_EMBARGO_TERMINATION_NON_ADMIN = Mail(
    'pending_embargo_termination_non_admin',
    subject='Request to end an embargo early for one of your projects.'
)

FILE_OPERATION_SUCCESS = Mail(
    'file_operation_success',
    subject='Your ${action} has finished',
)
FILE_OPERATION_FAILED = Mail(
    'file_operation_failed',
    subject='Your ${action} has failed',
)

UNESCAPE = '<% from website.util.sanitize import unescape_entities %> ${unescape_entities(src.title)}'
PROBLEM_REGISTERING = 'Problem registering ' + UNESCAPE

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
ARCHIVE_FILE_NOT_FOUND_DESK = Mail(
    'archive_file_not_found_desk',
    subject=PROBLEM_REGISTERING
)
ARCHIVE_FILE_NOT_FOUND_USER = Mail(
    'archive_file_not_found_user',
    subject='Registration failed because of altered files'
)

ARCHIVE_UNCAUGHT_ERROR_DESK = Mail(
    'archive_uncaught_error_desk',
    subject=PROBLEM_REGISTERING
)

ARCHIVE_REGISTRATION_STUCK_DESK = Mail(
    'archive_registration_stuck_desk',
    subject='[auto] Stuck registrations audit'
)

ARCHIVE_UNCAUGHT_ERROR_USER = Mail(
    'archive_uncaught_error_user',
    subject=PROBLEM_REGISTERING
)

ARCHIVE_SUCCESS = Mail(
    'archive_success',
    subject='Registration of ' + UNESCAPE + ' complete'
)

WELCOME = Mail(
    'welcome',
    subject='Welcome to the Open Science Framework'
)

WELCOME_OSF4I = Mail(
    'welcome_osf4i',
    subject='Welcome to the Open Science Framework'
)

PREREG_CHALLENGE_REJECTED = Mail(
    'prereg_challenge_rejected',
    subject='Revisions required, your submission for the Preregistration Challenge is not yet registered'
)

PREREG_CHALLENGE_ACCEPTED = Mail(
    'prereg_challenge_accepted',
    subject='Your research plan has been registered and accepted for the Preregistration Challenge'
)

PREREG_CSV = Mail(
    'prereg_csv',
    subject='[auto] Updated Prereg CSV'
)

EMPTY = Mail('empty', subject='${subject}')

SHARE_ERROR_DESK = Mail(
    'send_data_share_error_desk',
    subject='Share Error'
)

SHARE_PREPRINT_ERROR_DESK = Mail(
    'send_data_share_preprint_error_desk',
    subject='Share Error'
)

REVIEWS_SUBMISSION_CONFIRMATION = Mail(
    'reviews_submission_confirmation',
    subject='Confirmation of your submission to ${provider_name}'
)

ACCESS_REQUEST_SUBMITTED = Mail(
    'access_request_submitted',
    subject='An OSF user has requested access to your ${node.project_or_component}'
)

ACCESS_REQUEST_DENIED = Mail(
    'access_request_rejected',
    subject='Your access request to an OSF project has been declined.'
)
