import pytest
from django.core.management import call_command

from osf.models import NotableDomain
from osf.models.spam import SpamStatus
from osf_tests.factories import NodeFactory, UserFactory


@pytest.fixture()
def trusted_domain():
    return NotableDomain.objects.create(domain='trusted.edu', note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED)


@pytest.fixture()
def trusted_user(trusted_domain):
    user = UserFactory(username='someone@trusted.edu')
    user.emails.get_or_create(address='someone@trusted.edu')
    return user


@pytest.mark.django_db
class TestProtectedFromAutoSpam:

    def test_assumed_ham_user_cannot_be_auto_banned(self, trusted_user):
        trusted_user.confirm_spam(save=True)
        trusted_user.refresh_from_db()
        assert not trusted_user.is_spammy
        assert not trusted_user.is_disabled

    def test_assumed_ham_user_cannot_be_flagged(self, trusted_user):
        trusted_user.flag_spam()
        assert not trusted_user.is_spammy

    def test_ham_user_cannot_be_auto_banned(self):
        user = UserFactory()
        user.confirm_ham(save=True)
        user.confirm_spam(save=True)
        assert user.is_ham

    def test_user_with_ham_content_cannot_be_auto_banned(self):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.confirm_ham(save=True, train_spam_services=False)
        user.confirm_spam(save=True)
        assert not user.is_spammy

    def test_force_overrides_protection(self, trusted_user):
        trusted_user.confirm_spam(save=True, force=True, notify=False)
        trusted_user.refresh_from_db()
        assert trusted_user.is_spam

    def test_unprotected_user_is_banned(self):
        user = UserFactory()
        user.confirm_spam(save=True, notify=False)
        assert user.is_spam


@pytest.mark.django_db
class TestFindAssumedHamSpammyUsers:

    def test_report_only(self, trusted_user):
        trusted_user.confirm_spam(save=True, force=True, notify=False)
        call_command('find_assumed_ham_spammy_users')
        trusted_user.refresh_from_db()
        assert trusted_user.spam_status == SpamStatus.SPAM

    def test_fix(self, trusted_user, tmp_path):
        trusted_user.confirm_spam(save=True, force=True, notify=False)
        other = UserFactory()
        other.confirm_spam(save=True, notify=False)
        out = tmp_path / 'report.csv'
        call_command('find_assumed_ham_spammy_users', fix=True, output=str(out))
        trusted_user.refresh_from_db()
        other.refresh_from_db()
        assert trusted_user.spam_status == SpamStatus.UNKNOWN
        assert not trusted_user.is_disabled
        assert other.is_spam
        assert trusted_user._id in out.read_text()
        assert other._id not in out.read_text()
