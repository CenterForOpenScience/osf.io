import abc

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from unittest import mock

from framework.auth import Auth

from tests.base import DbTestCase
from osf_tests.factories import UserFactory, CommentFactory, ProjectFactory, PreprintFactory, RegistrationFactory, AuthUserFactory
from osf.models import NotableDomain, SpamStatus
from website import settings, mails


@pytest.mark.django_db
@mock.patch('framework.auth.views.mails.send_mail')
def test_throttled_autoban(mock_mail):
    settings.SPAM_THROTTLE_AUTOBAN = True
    user = AuthUserFactory()
    projects = []
    for _ in range(7):
        proj = ProjectFactory(creator=user)
        proj.flag_spam()
        proj.save()
        projects.append(proj)
    mock_mail.assert_called_with(osf_support_email=settings.OSF_SUPPORT_EMAIL,
            can_change_preferences=False,
            to_addr=user.username,
            user=user,
            mail=mails.SPAM_USER_BANNED)
    user.reload()
    assert user.is_disabled
    for project in projects:
        assert not project.is_public


@pytest.mark.enable_implicit_clean
class TestReportAbuse(DbTestCase):

    def setUp(self):
        super().setUp()
        self.comment = CommentFactory()
        self.auth = Auth(user=self.comment.user)

    def test_report_abuse(self):
        user = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
            user, date=time, category='spam', text='ads', save=True)
        assert self.comment.spam_status == SpamStatus.FLAGGED
        equivalent = dict(
            date=time,
            category='spam',
            text='ads',
            retracted=False
        )
        assert user._id in self.comment.reports
        assert self.comment.reports[user._id] == equivalent

    def test_report_abuse_own_comment(self):
        with pytest.raises(ValueError):
            self.comment.report_abuse(
                self.auth.user,
                category='spam', text='ads',
                save=True
            )
        assert self.comment.spam_status == SpamStatus.UNKNOWN

    def test_retract_report(self):
        user = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
            user, date=time, category='spam', text='ads', save=True
        )
        assert self.comment.spam_status == SpamStatus.FLAGGED
        self.comment.retract_report(user, save=True)
        assert self.comment.spam_status == SpamStatus.UNKNOWN
        equivalent = {
            'date': time,
            'category': 'spam',
            'text': 'ads',
            'retracted': True
        }
        assert user._id in self.comment.reports
        assert self.comment.reports[user._id] == equivalent

    def test_retract_report_not_reporter(self):
        reporter = UserFactory()
        non_reporter = UserFactory()
        self.comment.report_abuse(
            reporter, category='spam', text='ads', save=True
        )
        with pytest.raises(ValueError):
            self.comment.retract_report(non_reporter, save=True)
        assert self.comment.spam_status == SpamStatus.FLAGGED

    def test_retract_one_report_of_many(self):
        user_1 = UserFactory()
        user_2 = UserFactory()
        time = timezone.now()
        self.comment.report_abuse(
            user_1, date=time, category='spam', text='ads', save=True
        )
        assert self.comment.spam_status == SpamStatus.FLAGGED
        self.comment.report_abuse(
            user_2, date=time, category='spam', text='all', save=True
        )
        self.comment.retract_report(user_1, save=True)
        equivalent = {
            'date': time,
            'category': 'spam',
            'text': 'ads',
            'retracted': True
        }
        assert user_1._id in self.comment.reports
        assert self.comment.reports[user_1._id] == equivalent
        assert self.comment.spam_status == SpamStatus.FLAGGED

    def test_cannot_remove_flag_not_retracted(self):
        user = UserFactory()
        self.comment.report_abuse(
            user, category='spam', text='ads', save=True
        )
        self.comment.remove_flag(save=True)
        assert self.comment.spam_status == SpamStatus.FLAGGED

    def test_remove_flag(self):
        self.comment.flag_spam()
        self.comment.save()
        assert self.comment.spam_status == SpamStatus.FLAGGED
        self.comment.remove_flag(save=True)
        assert self.comment.spam_status == SpamStatus.UNKNOWN

    def test_validate_reports_bad_key(self):
        self.comment.reports[None] = {'category': 'spam', 'text': 'ads'}
        with pytest.raises(ValidationError):
            self.comment.save()

    def test_validate_reports_bad_type(self):
        self.comment.reports[self.auth.user._id] = 'not a dict'
        with pytest.raises(ValidationError):
            self.comment.save()

    def test_validate_reports_bad_value(self):
        self.comment.reports[self.auth.user._id] = {'foo': 'bar'}
        with pytest.raises(ValidationError):
            self.comment.save()


@pytest.mark.django_db
class TestSpamState:
    @pytest.fixture(params=[
        CommentFactory,
        ProjectFactory,
        PreprintFactory,
        RegistrationFactory,
        UserFactory,
    ])
    def spammable_thing(self, request):
        spammable_factory = request.param
        return spammable_factory()

    def test_flag_spam(self, spammable_thing):
        assert not spammable_thing.is_spammy
        assert not spammable_thing.is_spam
        spammable_thing.flag_spam()
        spammable_thing.save()
        assert spammable_thing.is_spammy
        assert not spammable_thing.is_spam

    def test_confirm_ham(self, spammable_thing):
        spammable_thing.confirm_ham(save=True)
        assert spammable_thing.is_ham

    def test_confirm_spam(self, spammable_thing):
        spammable_thing.confirm_spam(save=True)
        assert spammable_thing.is_spam

    @pytest.mark.parametrize('assume_ham', (True, False))
    @pytest.mark.parametrize('spam_status, expected_props', (
            (SpamStatus.UNKNOWN, {
                'is_spam': False,
                'is_spammy': False,
                'is_ham': False,
                'is_hammy': None,  # set in the test body based on assume_ham
            }),
            (SpamStatus.FLAGGED, {
                'is_spam': False,
                'is_spammy': True,
                'is_ham': False,
                'is_hammy': False,
            }),
            (SpamStatus.SPAM, {
                'is_spam': True,
                'is_spammy': True,
                'is_ham': False,
                'is_hammy': False,
            }),
            (SpamStatus.HAM, {
                'is_spam': False,
                'is_spammy': False,
                'is_ham': True,
                'is_hammy': True,
            }),
    ))
    def test_spam_status_properties(self, spammable_thing, assume_ham, spam_status, expected_props):
        if spam_status == SpamStatus.UNKNOWN:
            expected_props['is_hammy'] = assume_ham

        with mock.patch.object(type(spammable_thing), 'is_assumed_ham', new_callable=mock.PropertyMock) as mock_assumed_ham:
            mock_assumed_ham.return_value = assume_ham
            spammable_thing.spam_status = spam_status

            assert spammable_thing.is_spam == expected_props['is_spam']
            assert spammable_thing.is_spammy == expected_props['is_spammy']
            assert spammable_thing.is_ham == expected_props['is_ham']
            assert spammable_thing.is_hammy == expected_props['is_hammy']


@pytest.mark.django_db
class TestSpamCheckEmailDomain:
    @mock.patch('osf.models.spam.SpamMixin.do_check_spam', return_value=False)
    @mock.patch.object(settings, 'SPAM_SERVICES_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_CHECK_PUBLIC_ONLY', False)
    def test_trusted_domain(self, mock_do_check_spam):
        user = UserFactory()
        project = ProjectFactory()

        # spam check should normally call do_check_spam
        assert not mock_do_check_spam.called
        is_spam = project.check_spam(user, saved_fields={'title'}, request_headers={})
        assert not is_spam
        assert mock_do_check_spam.called

        # but what if we trust the user's email domain?
        user_email_address = user.emails.values_list('address', flat=True).first()
        user_email_domain = user_email_address.rpartition('@')[2].lower()
        NotableDomain.objects.create(
            domain=user_email_domain,
            note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED,
        )

        # should not call do_check_spam this time
        mock_do_check_spam.reset_mock()
        assert not mock_do_check_spam.called
        is_spam = project.check_spam(user, saved_fields={'title'}, request_headers={})
        assert not is_spam
        assert not mock_do_check_spam.called
