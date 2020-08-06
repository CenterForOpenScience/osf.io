import mock
import pytest

from django.utils import timezone

from osf_tests.factories import UserFactory
from website import mails

from osf.management.commands.email_all_users import email_all_users

class TestEmailAllUsers:

    @pytest.fixture()
    def user(self):
        return UserFactory(id=1)

    @pytest.fixture()
    def user2(self):
        return UserFactory(id=2)

    @pytest.fixture()
    def superuser(self):
        user = UserFactory()
        user.is_superuser = True
        user.save()
        return user

    @pytest.fixture()
    def deleted_user(self):
        return UserFactory(deleted=timezone.now())

    @pytest.fixture()
    def inactive_user(self):
        return UserFactory(is_disabled=True)

    @pytest.fixture()
    def unconfirmed_user(self):
        return UserFactory(date_confirmed=None)

    @pytest.fixture()
    def unregistered_user(self):
        return UserFactory(is_registered=False)

    @pytest.mark.django_db
    @mock.patch('website.mails.send_mail')
    def test_email_all_users_dry(self, mock_email, superuser):
        email_all_users('TOU_NOTIF', dry_run=True)

        mock_email.assert_called_with(
            to_addr=superuser.email,
            mail=mails.TOU_NOTIF,
            fullname=superuser.fullname
        )

    @pytest.mark.django_db
    @mock.patch('website.mails.send_mail')
    def test_dont_email_inactive_users(
            self, mock_email, deleted_user, inactive_user, unconfirmed_user, unregistered_user):

        email_all_users('TOU_NOTIF')

        mock_email.assert_not_called()

    @pytest.mark.django_db
    @mock.patch('website.mails.send_mail')
    def test_email_all_users_offset(self, mock_email, user, user2):
        email_all_users('TOU_NOTIF', offset=1, run=0)

        email_all_users('TOU_NOTIF', offset=1, run=1)

        email_all_users('TOU_NOTIF', offset=1, run=2)

        assert mock_email.call_count == 2
