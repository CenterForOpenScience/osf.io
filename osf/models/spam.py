import abc
import logging

from django.db import models
from django.utils import timezone

from osf.exceptions import ValidationValueError, ValidationTypeError
from osf.external.askismet import tasks as akismet_tasks
from osf.external.spam.tasks import check_resource_for_domains_postcommit, check_resource_with_spam_services
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import ensure_str, NonNaiveDateTimeField
from website import settings

logger = logging.getLogger(__name__)


def _validate_reports(value, *args, **kwargs):
    from osf.models import OSFUser
    for key, val in value.items():
        if not OSFUser.load(key):
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

    @property
    def is_ham(self):
        return self.spam_status == SpamStatus.HAM

    @property
    def is_hammy(self):
        return self.is_ham or (
            self.spam_status == SpamStatus.UNKNOWN and self.is_assumed_ham
        )

    @property
    def is_assumed_ham(self):
        """If True, will automatically skip spam checks.

        Override to set criteria for assumed ham.
        """
        return False

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

    def unspam(self, save=False):
        self.spam_status = SpamStatus.UNKNOWN
        if save:
            self.save()

    def confirm_ham(self, save=False, train_spam_services=True):
        self.spam_status = SpamStatus.HAM
        if save:
            self.save()

        if train_spam_services and self.spam_data:
            akismet_tasks.submit_ham.apply_async(
                kwargs=dict(
                    guid=self.guids.first()._id,
                )
            )

    def confirm_spam(self, domains=None, save=True, train_spam_services=True):
        if domains:
            if 'domains' in self.spam_data:
                self.spam_data['domains'].extend(domains)
                self.spam_data['domains'] = list(set(self.spam_data['domains']))
            else:
                self.spam_data['domains'] = domains
        elif train_spam_services and self.spam_data:
            akismet_tasks.submit_spam.apply_async(
                kwargs=dict(
                    guid=self.guids.first()._id,
                )
            )

        self.spam_status = SpamStatus.SPAM
        if save:
            self.save()

    @abc.abstractmethod
    def check_spam(self, user, saved_fields, request, save=False):
        """Must return is_spam"""
        pass

    def do_check_spam(self, author, author_email, content, request_headers):
        if self.is_hammy:
            return
        if self.is_spammy:
            return

        request_kwargs = {
            'remote_addr': request_headers.get('Remote-Addr') or request_headers.get('Host'),  # for local testing
            'user_agent': request_headers.get('User-Agent'),
            'referer': request_headers.get('Referer'),
        }
        request_kwargs.update(request_headers)

        check_resource_for_domains_postcommit(
            self.guids.first()._id,
            content,
        )

        if settings.SPAM_SERVICES_ENABLED:
            for key, value in request_kwargs.items():
                request_kwargs[key] = ensure_str(value)

            check_resource_with_spam_services(
                self.guids.first()._id,
                content,
                author,
                author_email,
                request_kwargs,
            )
