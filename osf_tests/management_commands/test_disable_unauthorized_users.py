import pytest
from unittest import mock

from osf.management.commands.disable_unauthorized_users import (
    disable_unauthorized_users,
    get_unauthorized_users,
)
from osf.models import OSFUser
from osf_tests.factories import UserFactory


@pytest.fixture(autouse=True)
def mock_mailchimp():
    with mock.patch('website.mailchimp_utils.unsubscribe_mailchimp'):
        yield


@pytest.mark.django_db
class TestDisableUnauthorizedUsers:

    @pytest.fixture()
    def cos_user(self):
        return UserFactory(username='staff@cos.io')

    @pytest.fixture()
    def outside_user(self):
        return UserFactory(username='outsider@example.com')

    @pytest.fixture()
    def lookalike_user(self):
        return UserFactory(username='lookalike@notcos.io')

    def test_get_unauthorized_users_excludes_cos_io_usernames(
        self, cos_user, outside_user, lookalike_user
    ):
        unauthorized = set(get_unauthorized_users())
        assert outside_user in unauthorized
        assert lookalike_user in unauthorized
        assert cos_user not in unauthorized

    def test_get_unauthorized_users_skips_already_disabled(self, outside_user):
        outside_user.is_disabled = True
        outside_user.save()
        assert outside_user not in set(get_unauthorized_users())

    def test_dry_run_does_not_disable(self, outside_user):
        count = disable_unauthorized_users(dry_run=True)
        outside_user.refresh_from_db()
        assert count == 1
        assert not outside_user.is_disabled

    def test_execute_disables_only_unauthorized_users(
        self, cos_user, outside_user, lookalike_user
    ):
        count = disable_unauthorized_users(dry_run=False)
        assert count == 2

        for user in (outside_user, lookalike_user):
            user.refresh_from_db()
            assert user.is_disabled

        assert not cos_user.is_disabled

    def test_execute_processes_multiple_batches(self, cos_user, outside_user, lookalike_user):
        count = disable_unauthorized_users(dry_run=False, batch_size=1)
        assert count == 2
        assert not get_unauthorized_users().exists()

        cos_user.refresh_from_db()
        assert not cos_user.is_disabled

    def test_execute_stops_when_disabling_fails(self, outside_user, lookalike_user):
        with mock.patch.object(OSFUser, 'deactivate_account', side_effect=Exception('failed_due_to_something')):
            count = disable_unauthorized_users(dry_run=False, batch_size=1)

        assert count == 0
        for user in (outside_user, lookalike_user):
            user.refresh_from_db()
            assert not user.is_disabled
