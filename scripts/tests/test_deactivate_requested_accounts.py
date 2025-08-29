import pytest

from osf_tests.factories import ProjectFactory, AuthUserFactory

from osf.management.commands.deactivate_requested_accounts import deactivate_requested_accounts


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_send_grid')
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

    def test_deactivate_user_with_no_content(self, mock_send_grid, user_requested_deactivation):

        deactivate_requested_accounts(dry_run=False)
        user_requested_deactivation.reload()

        assert user_requested_deactivation.requested_deactivation
        assert user_requested_deactivation.contacted_deactivation
        assert user_requested_deactivation.is_disabled
        mock_send_grid.assert_called()

    def test_deactivate_user_with_content(self, mock_send_grid, user_requested_deactivation_with_node):

        deactivate_requested_accounts(dry_run=False)
        user_requested_deactivation_with_node.reload()

        assert user_requested_deactivation_with_node.requested_deactivation
        assert not user_requested_deactivation_with_node.is_disabled
        mock_send_grid.assert_called()
