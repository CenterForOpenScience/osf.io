import pytest

from django.utils import timezone

from osf_tests.factories import UserFactory

from osf.management.commands.email_all_users import email_all_users
from tests.utils import capture_notifications

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
    def test_email_all_users_dry(self, superuser):
        with capture_notifications() as notifications:
            email_all_users('empty', dry_run=True, context={'subject': 'Test Dry Run', 'body': 'This is a test dry run email.'})

        assert len(notifications['emits']) == 1

    @pytest.mark.django_db
    def test_dont_email_inactive_users(
            self, deleted_user, inactive_user, unconfirmed_user, unregistered_user):
        with capture_notifications(expect_none=True):
            email_all_users('empty')

    @pytest.mark.django_db
    def test_email_all_users_offset(self, user, user2):
        with capture_notifications() as notifications:
            email_all_users('empty', offset=1, start_id=0, context={'subject': 'Test offset', 'body': 'This is a test offset email.'})
        assert len(notifications['emits']) == 1

        with capture_notifications() as notifications:
            email_all_users('empty', offset=1, start_id=1, context={'subject': 'Test offset', 'body': 'This is a test offset email.'})
        assert len(notifications['emits']) == 1

        with capture_notifications(expect_none=True):
            email_all_users('empty', offset=1, start_id=2, context={'subject': 'Test offset', 'body': 'This is a test offset email.'})
