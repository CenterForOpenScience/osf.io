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
import waffle

from mako.lookup import TemplateLookup, Template

from framework.email import tasks
from osf import features
from website import settings

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES_DIR = os.path.join(settings.TEMPLATES_PATH, 'emails')

_tpl_lookup = TemplateLookup(
    directories=[EMAIL_TEMPLATES_DIR],
)

HTML_EXT = '.html.mako'

DISABLED_MAILS = [
    'welcome',
    'welcome_osf4i'
]

class Mail(object):
    """An email object.

    :param str tpl_prefix: The template name prefix.
    :param str subject: The subject of the email.
    :param iterable categories: Categories to add to the email using SendGrid's
        SMTPAPI. Used for email analytics.
        See https://sendgrid.com/docs/User_Guide/Statistics/categories.html
    :param: bool engagement: Whether this is an engagement email that can be disabled with
        the disable_engagement_emails waffle flag
    """

    def __init__(self, tpl_prefix, subject, categories=None, engagement=False):
        self.tpl_prefix = tpl_prefix
        self._subject = subject
        self.categories = categories
        self.engagement = engagement

    def html(self, **context):
        """Render the HTML email message."""
        tpl_name = self.tpl_prefix + HTML_EXT
        return render_message(tpl_name, **context)

    def subject(self, **context):
        return Template(self._subject).render(**context)


def render_message(tpl_name, **context):
    """Render an email message."""
    tpl = _tpl_lookup.get_template(tpl_name)
    return tpl.render(**context)


def send_mail(
        to_addr, mail, from_addr=None, mailer=None, celery=True,
        username=None, password=None, callback=None, attachment_name=None,
        attachment_content=None, **context):
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
    if waffle.switch_is_active(features.DISABLE_ENGAGEMENT_EMAILS) and mail.engagement:
        return False

    from_addr = from_addr or settings.FROM_EMAIL
    mailer = mailer or tasks.send_email
    subject = mail.subject(**context)
    message = mail.html(**context)
    # Don't use ttls and login in DEBUG_MODE
    ttls = login = not settings.DEBUG_MODE
    logger.debug('Sending email...')
    logger.debug(u'To: {to_addr}\nFrom: {from_addr}\nSubject: {subject}\nMessage: {message}'.format(**locals()))

    kwargs = dict(
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        message=message,
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
    subject='OSF Account Verification'
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
    subject='OSF Account Verification'
)
EXTERNAL_LOGIN_LINK_SUCCESS = Mail(
    'external_confirm_success',
    subject='OSF Account Verification Success'
)

# Sign up confirmation emails for OSF, native campaigns and branded campaigns
INITIAL_CONFIRM_EMAIL = Mail(
    'initial_confirm',
    subject='OSF Account Verification'
)
CONFIRM_EMAIL = Mail(
    'confirm',
    subject='Add a new email to your OSF account'
)
CONFIRM_EMAIL_PREREG = Mail(
    'confirm_prereg',
    subject='OSF Account Verification, OSF Preregistration'
)
CONFIRM_EMAIL_ERPC = Mail(
    'confirm_erpc',
    subject='OSF Account Verification, Election Research Preacceptance Competition'
)
CONFIRM_EMAIL_PREPRINTS = lambda name, provider: Mail(
    'confirm_preprints_{}'.format(name),
    subject='OSF Account Verification, {}'.format(provider)
)
CONFIRM_EMAIL_REGISTRIES_OSF = Mail(
    'confirm_registries_osf',
    subject='OSF Account Verification, OSF Registries'
)
CONFIRM_EMAIL_MODERATION = lambda provider: Mail(
    'confirm_moderation',
    subject='OSF Account Verification, {}'.format(provider.name)
)

# Merge account, add or remove email confirmation emails.
CONFIRM_MERGE = Mail('confirm_merge', subject='Confirm account merge')
PRIMARY_EMAIL_CHANGED = Mail('primary_email_changed', subject='Primary email changed')


# Contributor added confirmation emails
INVITE_DEFAULT = Mail(
    'invite_default',
    subject='You have been added as a contributor to an OSF project.'
)
INVITE_OSF_PREPRINT = Mail(
    'invite_preprints_osf',
    subject='You have been added as a contributor to an OSF preprint.'
)
INVITE_PREPRINT = lambda provider: Mail(
    'invite_preprints',
    subject='You have been added as a contributor to {} {} {}.'.format(get_english_article(provider.name), provider.name, provider.preprint_word)
)
INVITE_DRAFT_REGISTRATION = Mail(
    'invite_draft_registration',
    subject='You have a new registration draft'
)
CONTRIBUTOR_ADDED_DEFAULT = Mail(
    'contributor_added_default',
    subject='You have been added as a contributor to an OSF project.'
)
CONTRIBUTOR_ADDED_OSF_PREPRINT = Mail(
    'contributor_added_preprints_osf',
    subject='You have been added as a contributor to an OSF preprint.'
)
CONTRIBUTOR_ADDED_PREPRINT = lambda provider: Mail(
    'contributor_added_preprints',
    subject=f'You have been added as a contributor to {get_english_article(provider.name)} {provider.name} {provider.preprint_word}.'
)
CONTRIBUTOR_ADDED_PREPRINT_NODE_FROM_OSF = Mail(
    'contributor_added_preprint_node_from_osf',
    subject='You have been added as a contributor to an OSF project.'
)
CONTRIBUTOR_ADDED_DRAFT_REGISTRATION = Mail(
    'contributor_added_draft_registration',
    subject='You have a new registration draft.'
)
MODERATOR_ADDED = lambda provider: Mail(
    'moderator_added',
    subject='You have been added as a moderator for {}'.format(provider.name)
)
CONTRIBUTOR_ADDED_ACCESS_REQUEST = Mail(
    'contributor_added_access_request',
    subject='Your access request to an OSF project has been approved'
)
FORWARD_INVITE = Mail('forward_invite', subject='Please forward to ${fullname}')
FORWARD_INVITE_REGISTERED = Mail('forward_invite_registered', subject='Please forward to ${fullname}')

FORGOT_PASSWORD = Mail('forgot_password', subject='Reset Password')
FORGOT_PASSWORD_INSTITUTION = Mail('forgot_password_institution', subject='Set Password')
PASSWORD_RESET = Mail('password_reset', subject='Your OSF password has been reset')
PENDING_VERIFICATION = Mail('pending_invite', subject='Your account is almost ready!')
PENDING_VERIFICATION_REGISTERED = Mail('pending_registered', subject='Received request to be a contributor')

REQUEST_EXPORT = Mail('support_request', subject='[via OSF] Export Request')
REQUEST_DEACTIVATION = Mail('support_request', subject='[via OSF] Deactivation Request')

REQUEST_DEACTIVATION_COMPLETE = Mail('request_deactivation_complete', subject='[via OSF] OSF account deactivated')

SPAM_USER_BANNED = Mail('spam_user_banned', subject='[OSF] Account flagged as spam')
SPAM_FILES_DETECTED = Mail(
    'spam_files_detected',
    subject='[auto] Spam files audit'
)

CONFERENCE_SUBMITTED = Mail(
    'conference_submitted',
    subject='Project created on OSF',
)
CONFERENCE_INACTIVE = Mail(
    'conference_inactive',
    subject='OSF Error: Conference inactive',
)
CONFERENCE_FAILED = Mail(
    'conference_failed',
    subject='OSF Error: No files attached',
)

DIGEST = Mail(
    'digest', subject='OSF Notifications',
    categories=['notifications', 'notifications-digest']
)

DIGEST_REVIEWS_MODERATORS = Mail(
    'digest_reviews_moderators',
    subject='Recent submissions to ${provider_name}',
)

TRANSACTIONAL = Mail(
    'transactional', subject='OSF: ${subject}',
    categories=['notifications', 'notifications-transactional']
)

# Retraction related Mail objects
PENDING_RETRACTION_ADMIN = Mail(
    'pending_retraction_admin',
    subject='Withdrawal pending for one of your registrations.'
)
PENDING_RETRACTION_NON_ADMIN = Mail(
    'pending_retraction_non_admin',
    subject='Withdrawal pending for one of your registrations.'
)
PENDING_RETRACTION_NON_ADMIN = Mail(
    'pending_retraction_non_admin',
    subject='Withdrawal pending for one of your projects.'
)
# Embargo related Mail objects
PENDING_EMBARGO_ADMIN = Mail(
    'pending_embargo_admin',
    subject='Admin decision pending for one of your registrations.'
)
PENDING_EMBARGO_NON_ADMIN = Mail(
    'pending_embargo_non_admin',
    subject='Admin decision pending for one of your registrations.'
)
# Registration related Mail Objects
PENDING_REGISTRATION_ADMIN = Mail(
    'pending_registration_admin',
    subject='Admin decision pending for one of your registrations.'
)
PENDING_REGISTRATION_NON_ADMIN = Mail(
    'pending_registration_non_admin',
    subject='Admin decision pending for one of your registrations.'
)
PENDING_EMBARGO_TERMINATION_ADMIN = Mail(
    'pending_embargo_termination_admin',
    subject='Request to end an embargo early for one of your registrations.'
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

UNESCAPE = '<% from osf.utils.sanitize import unescape_entities %> ${unescape_entities(src.title)}'
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
    subject='Welcome to OSF',
    engagement=True
)

WELCOME_OSF4I = Mail(
    'welcome_osf4i',
    subject='Welcome to OSF',
    engagement=True
)

EMPTY = Mail('empty', subject='${subject}')

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
    subject='Your access request to an OSF project has been declined'
)

CROSSREF_ERROR = Mail(
    'crossref_doi_error',
    subject='There was an error creating a DOI for preprint(s). batch_id: ${batch_id}'
)

CROSSREF_DOIS_PENDING = Mail(
    'crossref_doi_pending',
    subject='There are ${pending_doi_count} preprints with crossref DOI pending.'
)

WITHDRAWAL_REQUEST_GRANTED = Mail(
    'withdrawal_request_granted',
    subject='Your ${document_type} has been withdrawn',
)

GROUP_MEMBER_ADDED = Mail(
    'group_member_added',
    subject='You have been added as a ${permission} of the group ${group_name}',
)

GROUP_MEMBER_UNREGISTERED_ADDED = Mail(
    'group_member_unregistered_added',
    subject='You have been added as a ${permission} of the group ${group_name}',
)

GROUP_ADDED_TO_NODE = Mail(
    'group_added_to_node',
    subject='Your group, ${group_name}, has been added to an OSF Project'
)

WITHDRAWAL_REQUEST_DECLINED = Mail(
    'withdrawal_request_declined',
    subject='Your withdrawal request has been declined',
)

TOU_NOTIF = Mail(
    'tou_notif',
    subject='Updated Terms of Use for COS Websites and Services',
)

STORAGE_CAP_EXCEEDED_ANNOUNCEMENT = Mail(
    'storage_cap_exceeded_announcement',
    subject='Action Required to avoid disruption to your OSF project',
)

INSTITUTION_DEACTIVATION = Mail(
    'institution_deactivation',
    subject='Your OSF login has changed - here\'s what you need to know!'
)
