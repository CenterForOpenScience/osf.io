import pytest

from osf.models import NotificationType
from osf_tests.factories import ProjectFactory, AuthUserFactory

from osf.management.commands.deactivate_requested_accounts import deactivate_requested_accounts
from tests.utils import capture_notifications


@pytest.mark.django_db
class TestDeactivateRequestedAccount:

    @pytest.fixture()
    def user_requested_deactivation(self):
        user = AuthUserFactory(requested_deactivation=True)
        user.requested_deactivation = True
        user.save()
        return user

    @pytest.fixture()
    def user_requested_deactivation_with_node(self):
        user = AuthUserFactory(requested_deactivation=True)
        node = ProjectFactory(creator=user)
        node.save()
        user.save()
        return user

    def test_deactivate_user_with_no_content(self, user_requested_deactivation):

        with capture_notifications() as notifications:
            deactivate_requested_accounts(dry_run=False)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.DESK_REQUEST_DEACTIVATION
        user_requested_deactivation.reload()

        assert user_requested_deactivation.requested_deactivation
        assert user_requested_deactivation.contacted_deactivation
        assert user_requested_deactivation.is_disabled

    def test_deactivate_user_with_content(self, user_requested_deactivation_with_node):

        with capture_notifications() as notifications:
            deactivate_requested_accounts(dry_run=False)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.DESK_REQUEST_DEACTIVATION
        user_requested_deactivation_with_node.reload()

        assert user_requested_deactivation_with_node.requested_deactivation
        assert not user_requested_deactivation_with_node.is_disabled
