
import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory
from addons.dataverse.tests.factories import DataverseUserSettingsFactory

_mock = lambda attributes: type('MockObject', (mock.Mock,), attributes)


def mock_dataverse_client():
    return _mock({
        'get_dataverses': lambda: [
            _mock(
                {
                    'alias': 'Dataverse Test Alias',
                    'title': 'Dataverse Test Title',
                    'name': 'Dataverse Test Name',
                    'id': 'Dataverse Test ID',
                }
            )
        ],
        'get_service_document': _mock({}),
        'get_dataverse': lambda alias: _mock(
            {
                'title': 'FastBatman',
                'alias': alias,
                'id': 'WR',
                'name': 'Quez Watkins'
            }
        ),
    })


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

    @mock.patch('addons.dataverse.client.Connection', return_value=mock_dataverse_client())
    def test_addon_folders_PATCH(self, mock_client, app, node_with_authorized_addon, user):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/dataverse/',
            {
                'data': {
                    'attributes': {
                        'folder_id': 'test_123'
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'test_123'

    @mock.patch('addons.dataverse.client.Connection', return_value=mock_dataverse_client())
    def test_addon_credentials_PATCH(self, mock_client, app, node, user, enabled_addon):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/dataverse/',
            {
                'data': {
                    'attributes': {
                        'host': 'jakeelliot@eagles.bird',
                        'access_token': 'THEfranchise'
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
