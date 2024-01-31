import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory
from addons.bitbucket.tests.factories import BitbucketUserSettingsFactory

_mock = lambda attributes: type('MockObject', (mock.Mock,), attributes)


def mock_bitbucket_client():
    return _mock({
        'repos': lambda *args, **kwargs: [
            {
                'full_name': 'bitbucket-user-name/test-folder'
            }
        ],
        'repo': _mock({})
    })


@pytest.mark.django_db
class TestBitbucketConfig:
    """
    This class tests features added for our POSE grant which will enable us to access of Bitbucket Addon entirely via
    osf.io's v2 REST API. This requires giving the user the ability to configure the base folder for their bitbucket
    storage via the API.

    """

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('bitbucket', auth=Auth(user))
        addon.user_settings = BitbucketUserSettingsFactory(owner=user)
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(provider='bitbucket')
        enabled_addon.external_account = external_account
        user_settings = enabled_addon.user_settings
        user_settings.oauth_grants[node._id] = {enabled_addon.external_account._id: []}
        user_settings.save()
        user.external_accounts.add(external_account)
        user.save()
        enabled_addon.save()
        return node

    @mock.patch('addons.bitbucket.models.BitbucketClient', return_value=mock_bitbucket_client())
    def test_addon_folders_PATCH(self, mock_bitbucket, app, node_with_authorized_addon, user):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/bitbucket/',
            {
                'data': {
                    'attributes': {
                        'folder_id': 'bitbucket-user-name/test-folder'
                    }
                }
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'test-folder'
        assert resp.json['data']['attributes']['folder_path'] == 'test-folder'
