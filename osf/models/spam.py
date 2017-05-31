import abc
import logging

from django.db import models
from django.utils import timezone
from osf.exceptions import ValidationValueError, ValidationTypeError
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField

from website import settings
from website.project.model import User
from website.util import akismet
from website.util.akismet import AkismetClientError

logger = logging.getLogger(__name__)


def _get_client():
    return akismet.AkismetClient(
        apikey=settings.AKISMET_APIKEY,
        website=settings.DOMAIN,
        verify=True
    )


def _validate_reports(value, *args, **kwargs):
    for key, val in value.iteritems():
        if not User.load(key):
            raise ValidationValueError('Keys must be user IDs')
        if not isinstance(val, dict):
            raise ValidationTypeError('Values must be dictionaries')
        if ('category' not in val or 'text' not in val or 'date' not in val or 'retracted' not in val):
            raise ValidationValueError(
                ('Values must include `date`, `category`, ',
                 '`text`, `retracted` keys')
            )


class SpamStatus(object):
    UNKNOWN = None
    FLAGGED = 1
    SPAM = 2
    HAM = 4


class SpamMixin(models.Model):
    """Mixin to add to objects that can be marked as spam.
    """

    class Meta:
        abstract = True

    # # Node fields that trigger an update to search on save
    # SPAM_UPDATE_FIELDS = {
    #     'spam_status',
    # }
    spam_status = models.IntegerField(default=SpamStatus.UNKNOWN, null=True, blank=True, db_index=True)
    spam_pro_tip = models.CharField(default=None, null=True, blank=True, max_length=200)
    # Data representing the original spam indication
    # - author: author name
    # - author_email: email of the author
    # - content: data flagged
    # - headers: request headers
    #   - Remote-Addr: ip address from request
    #   - User-Agent: user agent from request
    #   - Referer: referrer header from request (typo +1, rtd)
    spam_data = DateTimeAwareJSONField(default=dict, blank=True)
    date_last_reported = NonNaiveDateTimeField(default=None, null=True, blank=True, db_index=True)

    # Reports is a dict of reports keyed on reporting user
    # Each report is a dictionary including:
    #  - date: date reported
    #  - retracted: if a report has been retracted
    #  - category: What type of spam does the reporter believe this is
    #  - text: Comment on the comment
    reports = DateTimeAwareJSONField(
        default=dict, blank=True, validators=[_validate_reports]
    )

    def flag_spam(self):
        # If ham and unedited then tell user that they should read it again
        if self.spam_status == SpamStatus.UNKNOWN:
            self.spam_status = SpamStatus.FLAGGED

    def remove_flag(self, save=False):
        if self.spam_status != SpamStatus.FLAGGED:
            return
        for report in self.reports.values():
            if not report.get('retracted', True):
                return
        self.spam_status = SpamStatus.UNKNOWN
        if save:
            self.save()

    @property
    def is_spam(self):
        return self.spam_status == SpamStatus.SPAM

    @property
    def is_spammy(self):
        return self.spam_status in [SpamStatus.FLAGGED, SpamStatus.SPAM]

    def report_abuse(self, user, save=False, **kwargs):
        """Report object is spam or other abuse of OSF

        :param user: User submitting report
        :param save: Save changes
        :param kwargs: Should include category and message
        :raises ValueError: if user is reporting self
        """
        if user == self.user:
            raise ValueError('User cannot report self.')
        self.flag_spam()
        date = timezone.now()
        report = {'date': date, 'retracted': False}
        report.update(kwargs)
        if 'text' not in report:
            report['text'] = None
        self.reports[user._id] = report
        self.date_last_reported = report['date']
        if save:
            self.save()

    def retract_report(self, user, save=False):
        """Retract last report by user

        Only marks the last report as retracted because there could be
        history in how the object is edited that requires a user
        to flag or retract even if object is marked as HAM.
        :param user: User retracting
        :param save: Save changes
        """
        if user._id in self.reports:
            if not self.reports[user._id]['retracted']:
                self.reports[user._id]['retracted'] = True
                self.remove_flag()
        else:
            raise ValueError('User has not reported this content')
        if save:
            self.save()

    def confirm_ham(self, save=False):
        # not all mixins will implement check spam pre-req, only submit ham when it was incorrectly flagged
        if (
            settings.SPAM_CHECK_ENABLED and
            self.spam_data and self.spam_status in [SpamStatus.FLAGGED, SpamStatus.SPAM]
        ):
            client = _get_client()
            client.submit_ham(
                user_ip=self.spam_data['headers']['Remote-Addr'],
                user_agent=self.spam_data['headers'].get('User-Agent'),
                referrer=self.spam_data['headers'].get('Referer'),
                comment_content=self.spam_data['content'],
                comment_author=self.spam_data['author'],
                comment_author_email=self.spam_data['author_email'],
            )
            logger.info('confirm_ham update sent')
        self.spam_status = SpamStatus.HAM
        if save:
            self.save()

    def confirm_spam(self, save=False):
        # not all mixins will implement check spam pre-req, only submit spam when it was incorrectly flagged
        if (
            settings.SPAM_CHECK_ENABLED and
            self.spam_data and self.spam_status in [SpamStatus.UNKNOWN, SpamStatus.HAM]
        ):
            client = _get_client()
            client.submit_spam(
                user_ip=self.spam_data['headers']['Remote-Addr'],
                user_agent=self.spam_data['headers'].get('User-Agent'),
                referrer=self.spam_data['headers'].get('Referer'),
                comment_content=self.spam_data['content'],
                comment_author=self.spam_data['author'],
                comment_author_email=self.spam_data['author_email'],
            )
            logger.info('confirm_spam update sent')
        self.spam_status = SpamStatus.SPAM
        if save:
            self.save()

    @abc.abstractmethod
    def check_spam(self, user, saved_fields, request_headers, save=False):
        """Must return is_spam"""
        pass

    def do_check_spam(self, author, author_email, content, request_headers):
        if self.spam_status == SpamStatus.HAM:
            return False
        if self.is_spammy:
            return True

        client = _get_client()
        remote_addr = request_headers['Remote-Addr']
        user_agent = request_headers.get('User-Agent')
        referer = request_headers.get('Referer')
        try:
            is_spam, pro_tip = client.check_comment(
                user_ip=remote_addr,
                user_agent=user_agent,
                referrer=referer,
                comment_content=content,
                comment_author=author,
                comment_author_email=author_email
            )
        except AkismetClientError:
            logger.exception('Error performing SPAM check')
            return False
        self.spam_pro_tip = pro_tip
        self.spam_data['headers'] = {
            'Remote-Addr': remote_addr,
            'User-Agent': user_agent,
            'Referer': referer,
        }
        self.spam_data['content'] = content
        self.spam_data['author'] = author
        self.spam_data['author_email'] = author_email
        if is_spam:
            self.flag_spam()
        return is_spam
