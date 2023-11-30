import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory

mock_return = lambda attributes: type('MockObject', (mock.Mock,), attributes)


@pytest.mark.django_db
class TestBoaConfig:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('boa', auth=Auth(user))
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(provider='boa')
        enabled_addon.external_account = external_account
        user_settings = user.get_or_add_addon('boa')
        user_settings.save()
        enabled_addon.user_settings = user_settings
        user.external_accounts.add(external_account)
        user.save()
        enabled_addon.save()
        return node

    def test_addon_folders_PATCH(self, app, node_with_authorized_addon, user):

        payload = {'data': {'attributes': {'folder_path': 'john.e.tordoff/test-project', 'folder_id': '52343250'}}}

        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/boa/',
            payload,
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'john.e.tordoff/test-project'
        assert resp.json['data']['attributes']['folder_path'] == 'john.e.tordoff/test-project'

    def test_addon_credentials_PATCH(self, app, node, user, enabled_addon):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/boa/',
            {
                'data': {
                    'attributes': {
                        'username': 'johntordoff',
                        'password': 'Quez_Watkins',
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
