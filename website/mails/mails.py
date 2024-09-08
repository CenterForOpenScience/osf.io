# -*- coding: utf-8 -*-
"""GakuNin RDM mailing utilities.

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
    input_encoding='utf-8',
    output_encoding='utf-8',
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

    def __init__(self, tpl_prefix, subject, categories=None, engagement=False, _charset='ISO-2022-JP'):
        self.tpl_prefix = tpl_prefix
        self._subject = subject
        self.categories = categories
        self.engagement = engagement
        self._charset = _charset

    def html(self, **context):
        """Render the HTML email message."""
        tpl_name = self.tpl_prefix + HTML_EXT
        return render_message(tpl_name, **context)

    def subject(self, **context):
        return Template(self._subject, input_encoding='utf-8', output_encoding='utf-8').render_unicode(**context)

    @property
    def charset(self):
        return self.__charset

    @charset.setter
    def charset(self, _charset):
        self.__charset = _charset


def render_message(tpl_name, **context):
    """Render an email message."""
    tpl = _tpl_lookup.get_template(tpl_name)
    return tpl.render_unicode(**context)


def send_mail(
        to_addr, mail, mimetype='html', from_addr=None, mailer=None, celery=True,
        username=None, password=None, callback=None, attachment_name=None,
        attachment_content=None, cc_addr=None, replyto=None, _charset='utf-8', **context):
    """Send an email from the GakuNin RDM.
    Example: ::

        from website import mails

        mails.send_email('foo@bar.com', mails.TEST, name="Foo")

    :param str to_addr: The recipient's email address(es)
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

    if hasattr(settings, 'TO_EMAIL_FOR_DEBUG') and \
       settings.TO_EMAIL_FOR_DEBUG is not None and \
       settings.TO_EMAIL_FOR_DEBUG is not '':
        subject = 'DEBUG:' + subject + ' (To:' + to_addr + ')'
        to_addr = settings.TO_EMAIL_FOR_DEBUG

    logger.debug('Sending email...')
    logger.debug(u'To: {to_addr}\nFrom: {from_addr}\nSubject: {subject}\nMessage: {message}'.format(**locals()))

    kwargs = dict(
        from_addr=from_addr,
        to_addr=to_addr,
        cc_addr=cc_addr,
        replyto=replyto,
        subject=subject,
        message=message,
        _charset=mail._charset,
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
    subject='GakuNin RDM Account Verification'
)

FORK_COMPLETED = Mail(
    'fork_completed',
    subject='フォークが完了しました / Your fork has completed'
)

FORK_FAILED = Mail(
    'fork_failed',
    subject='フォークに失敗しました / Your fork has failed'
)

EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK = Mail(
    'external_confirm_link',
    subject='GakuNin RDM Account Verification'
)
EXTERNAL_LOGIN_LINK_SUCCESS = Mail(
    'external_confirm_success',
    subject='GakuNin RDM Account Verification Success'
)

# Sign up confirmation emails for GakuNin RDM, native campaigns and branded campaigns
INITIAL_CONFIRM_EMAIL = Mail(
    'initial_confirm',
    subject='GakuNin RDM Account Verification'
)
CONFIRM_EMAIL = Mail(
    'confirm',
    subject='GakuNin RDMアカウントのメールアドレス追加 / Add a new email to your GakuNin RDM account'
)
CONFIRM_EMAIL_PREREG = Mail(
    'confirm_prereg',
    subject='GakuNin RDM Account Verification, GakuNin RDM Preregistration'
)
CONFIRM_EMAIL_ERPC = Mail(
    'confirm_erpc',
    subject='GakuNin RDM Account Verification, Election Research Preacceptance Competition'
)
CONFIRM_EMAIL_PREPRINTS = lambda name, provider: Mail(
    'confirm_preprints_{}'.format(name),
    subject='GakuNin RDM Account Verification, {}'.format(provider)
)
CONFIRM_EMAIL_REGISTRIES_OSF = Mail(
    'confirm_registries_osf',
    subject='GakuNin RDM Account Verification, GakuNin RDM Registries'
)
CONFIRM_EMAIL_MODERATION = lambda provider: Mail(
    'confirm_moderation',
    subject='GakuNin RDM Account Verification, {}'.format(provider.name)
)

# Merge account, add or remove email confirmation emails.
CONFIRM_MERGE = Mail('confirm_merge', subject='アカウントの統合確認 / Confirm account merge')
REMOVED_EMAIL = Mail('email_removed', subject='GakuNin RDMアカウントのメールアドレス削除 / Email address removed from your GakuNin RDM account')
PRIMARY_EMAIL_CHANGED = Mail('primary_email_changed', subject='プライバリメールアドレスの変更 / Primary email changed')


# Contributor added confirmation emails
INVITE_DEFAULT = Mail(
    'invite_default',
    subject='You have been added as a contributor to a GakuNin RDM project.'
)
INVITE_PREPRINT = lambda template, provider: Mail(
    'invite_preprints_{}'.format(template),
    subject='You have been added as a contributor to {} {} {}.'.format(get_english_article(provider.name), provider.name, provider.preprint_word)
)
CONTRIBUTOR_ADDED_DEFAULT = Mail(
    'contributor_added_default',
    subject='GakuNin RDMプロジェクトのメンバーに追加されました / You have been added as a contributor to a GakuNin RDM project.'
)
CONTRIBUTOR_ADDED_PREPRINT = lambda template, provider: Mail(
    'contributor_added_preprints_{}'.format(template),
    subject='You have been added as a contributor to {} {} {}.'.format(get_english_article(provider.name), provider.name, provider.preprint_word)
)
CONTRIBUTOR_ADDED_PREPRINT_NODE_FROM_OSF = Mail(
    'contributor_added_preprint_node_from_osf',
    subject='You have been added as a contributor to a GakuNin RDM project.'
)
CONTRIBUTOR_ADDED_DRAFT_REGISTRATION = Mail(
    'contributor_added_draft_registration',
    subject='You have been added as a contributor to a draft registration.'
)
MODERATOR_ADDED = lambda provider: Mail(
    'moderator_added',
    subject='You have been added as a moderator for {}'.format(provider.name)
)
PREPRINT_CONFIRMATION_DEFAULT = Mail(
    'preprint_confirmation_default',
    subject="You've shared a preprint on GakuNin RDM preprints"
)
CONTRIBUTOR_ADDED_ACCESS_REQUEST = Mail(
    'contributor_added_access_request',
    subject='GakuNin RDMプロジェクトへのアクセス申請が承認されました / Your access request to a GakuNin RDM project has been approved'
)
FORWARD_INVITE = Mail('forward_invite', subject='Please forward to ${fullname}')
FORWARD_INVITE_REGISTERED = Mail('forward_invite_registered', subject='Please forward to ${fullname}')

FORGOT_PASSWORD = Mail('forgot_password', subject='Reset Password')
PASSWORD_RESET = Mail('password_reset', subject='Your GakuNin RDM password has been reset')
PENDING_VERIFICATION = Mail('pending_invite', subject='Your account is almost ready!')
PENDING_VERIFICATION_REGISTERED = Mail('pending_registered', subject='Received request to be a contributor')

REQUEST_EXPORT = Mail('support_request', subject='[GakuNin RDM経由]出力リクエスト / [via GakuNin RDM] Export Request')
REQUEST_DEACTIVATION = Mail('support_request', subject='[GakuNin RDM経由]認証解除リクエスト / Deactivation Request')

REQUEST_DEACTIVATION_COMPLETE = Mail('request_deactivation_complete', subject='[via GakuNin RDM] GakuNin RDM account deactivated')

SPAM_USER_BANNED = Mail('spam_user_banned', subject='[GakuNin RDM]アカウントにスパムの疑いがあります / [GakuNin RDM] Account flagged as spam')

CONFERENCE_SUBMITTED = Mail(
    'conference_submitted',
    subject='Project created on GakuNin RDM',
)
CONFERENCE_INACTIVE = Mail(
    'conference_inactive',
    subject='GakuNin RDM Error: Conference inactive',
)
CONFERENCE_FAILED = Mail(
    'conference_failed',
    subject='GakuNin RDM Error: No files attached',
)

DIGEST = Mail(
    'digest', subject='GakuNin RDM からの通知 / GakuNin RDM Notifications',
    categories=['notifications', 'notifications-digest']
)

DIGEST_REVIEWS_MODERATORS = Mail(
    'digest_reviews_moderators',
    subject='Recent submissions to ${provider_name}',
)

TRANSACTIONAL = Mail(
    'transactional', subject='GakuNin RDM: ${subject}',
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
    subject='GakuNin RDMにようこそ / Welcome to the GakuNin RDM',
    engagement=True
)

WELCOME_OSF4I = Mail(
    'welcome_osf4i',
    subject='Welcome to the GakuNin RDM',
    engagement=True
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
    subject='GakuNin RDMのユーザーからあなたの${u"プロジェクト" if node.project_or_component == "project" else u"コンポーネント"}へのアクセスの要求がありました / A GakuNin RDM user has requested access to your ${node.project_or_component}'
)

ACCESS_REQUEST_DENIED = Mail(
    'access_request_rejected',
    subject='GakuNin RDMプロジェクトへのアクセス申請が拒否されました / Your access request to a GakuNin RDM project has been declined'
)

CROSSREF_ERROR = Mail(
    'crossref_doi_error',
    subject='There was an error creating a DOI for preprint(s). batch_id: ${batch_id}'
)

CROSSREF_DOIS_PENDING = Mail(
    'crossref_doi_pending',
    subject='There are ${pending_doi_count} preprints with crossref DOI pending.'
)

PREPRINT_WITHDRAWAL_REQUEST_GRANTED = Mail(
    'preprint_withdrawal_request_granted',
    subject='Your ${reviewable.provider.preprint_word} has been withdrawn',
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

PREPRINT_WITHDRAWAL_REQUEST_DECLINED = Mail(
    'preprint_withdrawal_request_declined',
    subject='Your withdrawal request has been declined',
)

TOU_NOTIF = Mail(
    'tou_notif',
    subject='Updated Terms of Use for COS Websites and Services',
)
