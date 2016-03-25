from datetime import datetime

from modularodm import fields
from modularodm.exceptions import ValidationTypeError, ValidationValueError

from framework.mongo import StoredObject
from website.project.model import User


def validate_reports(value, *args, **kwargs):
    for key, val in value.iteritems():
        if not User.load(key):
            raise ValidationValueError('Keys must be user IDs')
        if not isinstance(val, dict):
            raise ValidationTypeError('Values must be dictionaries')
        if (
            'category' not in val or
            'text' not in val or
            'date' not in val or
            'retracted' not in val
        ):
            raise ValidationValueError(
                ('Values must include `date`, `category`, ',
                 '`text`, `retracted` keys')
            )


class SpamMixin(StoredObject):
    """Mixin to add to objects that can be marked as spam.
    """

    _meta = {
        'abstract': True
    }

    UNKNOWN = 0
    FLAGGED = 1
    SPAM = 2
    HAM = 4

    spam_status = fields.IntegerField(default=UNKNOWN, index=True)
    latest_report = fields.DateTimeField(default=None, index=True)

    # Reports is a dict of reports keyed on reporting user
    # Each report is a dictionary including:
    #  - date: date reported
    #  - retracted: if a report has been retracted
    #  - category: What type of spam does the reporter believe this is
    #  - text: Comment on the comment
    reports = fields.DictionaryField(
        default=dict, validate=validate_reports
    )

    def flag_spam(self, save=False):
        # If ham and unedited then tell user that they should read it again
        if self.spam_status == self.UNKNOWN:
            self.spam_status = self.FLAGGED
        if save:
            self.save()

    def remove_flag(self, save=False):
        if self.spam_status != self.FLAGGED:
            return
        for report in self.reports.values():
            if not report.get('retracted', True):
                return
        self.spam_status = self.UNKNOWN
        if save:
            self.save()

    def confirm_ham(self, save=False):
        self.spam_status = self.HAM
        if save:
            self.save()

    def confirm_spam(self, save=False):
        self.spam_status = self.SPAM
        if save:
            self.save()

    @property
    def is_spam(self):
        return self.spam_status == self.SPAM

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
        date = datetime.utcnow()
        report = {'date': date, 'retracted': False}
        report.update(kwargs)
        if 'text' not in report:
            report['text'] = None
        self.reports[user._id] = report
        self.latest_report = report['date']
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
