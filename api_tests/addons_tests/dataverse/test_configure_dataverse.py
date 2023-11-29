
import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory
from addons.dataverse.tests.factories import DataverseUserSettingsFactory

mock_return = lambda attributes: type('MockObject', (mock.Mock,), attributes)


@pytest.mark.django_db
class TestDataverseConfig:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('dataverse', auth=Auth(user))
        addon.user_settings = DataverseUserSettingsFactory(owner=user)
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(provider='dataverse')
        enabled_addon.external_account = external_account
        user_settings = enabled_addon.user_settings
        user_settings.save()
        user.external_accounts.add(external_account)
        user.save()
        enabled_addon.save()
        return node

    @mock.patch('addons.dataverse.client.Connection')
    def test_addon_folders_PATCH(self, mock_client, app, node_with_authorized_addon, user):
        mock_return = lambda attributes: type('MockObject', (mock.Mock,), attributes)

        mock_client.return_value = mock_return({
            'get_service_document': mock_return({}),
            'get_dataverse': lambda alias: mock_return(
                {
                    'title': 'FastBatman',
                    'alias': alias,
                    'id': 'SwoleBatman'
                }
            )
        })

        payload = {'data': {'attributes': {'folder_id': 'test_123'}}}

        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/dataverse/',
            payload,
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'test-folder'
        assert resp.json['data']['attributes']['folder_path'] == 'test-folder'

    @mock.patch('addons.dataverse.client.Connection')
    def test_addon_credentials_PATCH(self, mock_client, app, node, user, enabled_addon):
        mock_return = lambda attributes: type('MockObject', (mock.Mock,), attributes)

        mock_client.return_value = mock_return({
            'get_service_document': mock_return({})
        })

        payload = {'data': {'attributes': {'host': 'jakeelliot@eagles.bird', 'access_token': 'access_token'}}}

        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/dataverse/',
            payload,
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
