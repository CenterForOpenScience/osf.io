import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory

_mock = lambda attributes: type('MockObject', (mock.Mock,), attributes)


def mock_gitlab_client():
    return _mock({
        'gitlab': _mock({
            'auth': lambda *args, **kwargs: True,
            'user': _mock({
                'username': 'WeaponX',
                'web_url': 'https://BrianDawkins@eagles.bird'
            })
        })
    })


@pytest.mark.django_db
class TestGitlabConfig:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('gitlab', auth=Auth(user))
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(provider='gitlab')
        enabled_addon.external_account = external_account
        user_settings = user.get_or_add_addon('gitlab')
        user_settings.save()
        enabled_addon.user_settings = user_settings
        user.external_accounts.add(external_account)
        user.save()
        enabled_addon.save()
        return node

    @mock.patch('api.nodes.serializers.GitLabClient', return_value=mock_gitlab_client())
    def test_addon_folders_PATCH(self, mock_client, app, node_with_authorized_addon, user):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/gitlab/',
            {
                'data': {
                    'attributes': {
                        'folder_path': 'john.e.tordoff/test-project',
                        'folder_id': '52343250'
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'john.e.tordoff/test-project'
        assert resp.json['data']['attributes']['folder_path'] == 'john.e.tordoff/test-project'

    @mock.patch('api.nodes.serializers.GitLabClient', return_value=mock_gitlab_client())
    def test_addon_credentials_PATCH(self, mock_client, app, node, user, enabled_addon):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/gitlab/',
            {
                'data': {
                    'attributes': {
                        'host': 'https://hasanreddick@eagles.bird',
                        'access_token': 'JoshSweat'
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
