import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory

_mock = lambda attributes: type('MockObject', (mock.Mock,), attributes)

def mock_owncloud_client():
    return _mock({
        'login': lambda username, password: None,
        'logout': lambda: None,
        'list': lambda folder: [folder]
    })


@pytest.mark.django_db
class TestOwnCloudConfig:
    """
    This class tests for new Owncloud Addon behavior created by the POSE grant. This new behavior allows a user access
    two additional features via the API.

    1. Adds ability to add credentials via v2 API tested in `test_addon_credentials_PATCH`
    2. Adds ability to set owncloud base folders via v2 API tested in `test_addon_credentials_PATCH`

    This also adds validation for setting owncloud folder_id's checking them againest the owncloud server.
    """

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('owncloud', auth=Auth(user))
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(
            provider='owncloud',
            display_name='test_username',
            oauth_key='test_password',
            oauth_secret='http://test_host.com',
        )
        enabled_addon.external_account = external_account
        user_settings = user.get_or_add_addon('owncloud')
        enabled_addon.user_settings = user_settings
        user.external_accounts.add(external_account)
        user.save()
        user_settings.save()
        enabled_addon.save()
        return node

    @mock.patch('addons.owncloud.models.OwnCloudClient', return_value=mock_owncloud_client())
    def test_addon_folders_PATCH(self, mock_client, app, node_with_authorized_addon, user):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/owncloud/',
            {
                'data': {
                    'attributes': {
                        'folder_id': '/'}
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == '/'
        assert resp.json['data']['attributes']['folder_path'] == '/'

    @mock.patch('api.nodes.serializers.OwnCloudClient', return_value=mock_owncloud_client())
    def test_addon_credentials_PATCH(self, mock_client, app, node, user, enabled_addon):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/owncloud/',
            {
                'data': {
                    'attributes': {
                        'username': 'FastBatman',
                        'password': 'Quez_Watkins',
                        'host': 'https://sirianni@eagles.bird',
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
