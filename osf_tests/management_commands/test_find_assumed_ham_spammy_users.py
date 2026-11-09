from unittest import mock

import pytest
from django.core.management import call_command

from osf.models import NotableDomain
from osf.models.admin_log_entry import CONFIRM_SPAM, update_admin_log
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


@pytest.mark.django_db
class TestFindAssumedHamSpammyUsersSafety:

    @pytest.fixture()
    def spammed_trusted_user(self, trusted_user):
        trusted_user.confirm_spam(save=True, force=True, notify=False)
        return trusted_user

    @pytest.mark.parametrize('use_guid', [True, False])
    def test_fix_skips_users_spammed_by_staff(self, spammed_trusted_user, use_guid, tmp_path):
        admin = UserFactory()
        update_admin_log(
            user_id=admin.id,
            object_id=spammed_trusted_user._id if use_guid else spammed_trusted_user.id,
            object_repr='User',
            message='Confirmed SPAM',
            action_flag=CONFIRM_SPAM,
        )
        out = tmp_path / 'report.csv'
        call_command('find_assumed_ham_spammy_users', fix=True, output=str(out))
        spammed_trusted_user.refresh_from_db()
        assert spammed_trusted_user.spam_status == SpamStatus.SPAM
        assert 'needs_review' in out.read_text()

    def test_fix_skips_users_reported_by_other_users(self, spammed_trusted_user):
        spammed_trusted_user.reports = {'someone': {'retracted': False}}
        spammed_trusted_user.save()
        call_command('find_assumed_ham_spammy_users', fix=True)
        spammed_trusted_user.refresh_from_db()
        assert spammed_trusted_user.spam_status == SpamStatus.SPAM

    def test_fix_does_not_touch_self_requested_deactivation(self, trusted_user):
        trusted_user.requested_deactivation = True
        trusted_user.is_disabled = True
        trusted_user.spam_status = SpamStatus.FLAGGED
        trusted_user.save()
        with mock.patch('website.mailchimp_utils.subscribe_on_confirm') as subscribe:
            call_command('find_assumed_ham_spammy_users', fix=True)
        trusted_user.refresh_from_db()
        assert trusted_user.spam_status == SpamStatus.UNKNOWN
        assert trusted_user.is_disabled
        assert trusted_user.requested_deactivation
        subscribe.assert_not_called()

    def test_report_lists_spammed_resources(self, spammed_trusted_user, tmp_path):
        node = NodeFactory(creator=spammed_trusted_user)
        node.confirm_spam(save=True, train_spam_services=False, notify=False)
        out = tmp_path / 'report.csv'
        call_command('find_assumed_ham_spammy_users', output=str(out))
        assert node._id in out.read_text()
