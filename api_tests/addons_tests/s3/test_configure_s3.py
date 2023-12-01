import mock
import pytest
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import ProjectFactory, AuthUserFactory, ExternalAccountFactory
from addons.s3.tests.factories import S3UserSettingsFactory


def _mock_s3_client():
    """
    Mock client for boto.s3.connection.S3Connection
    """
    _mock = lambda attributes: type('MockObject', (mock.Mock,), attributes)
    return _mock({
        'get_all_buckets': _mock({
            'owner': _mock({
                'display_name': 'Jalen Hurts',
                'id': '#1',
            }),
        }),
        'head_bucket': _mock({}),
        'get_bucket': _mock({
            'get_location': lambda *args, **kwargs: 'us-west-1',
        }),
    })


@pytest.mark.django_db
class TestS3Config:
    """
    This tests features added as part of the the POSE grant, these features should allow our Amazon S3 addons to be
    fully configured via osf.io's REST API, instead of relying on the legacy FE.
    Features added:

    1. Ability to add credentials via API tested in `test_addon_credentials_PATCH`
    2. Ability to configure AWS Bucket and base folders entirely via API in tested in `test_addon_folders_PATCH`
    """

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def enabled_addon(self, node, user):
        addon = node.get_or_add_addon('s3', auth=Auth(user))
        addon.user_settings = S3UserSettingsFactory(owner=user)
        addon.save()
        return addon

    @pytest.fixture()
    def node_with_authorized_addon(self, user, node, enabled_addon):
        external_account = ExternalAccountFactory(provider='s3')
        user.external_accounts.add(external_account)
        enabled_addon.external_account = external_account
        enabled_addon.save()
        return node

    @mock.patch('addons.s3.utils.S3Connection', return_value=_mock_s3_client())
    def test_addon_credentials_PATCH(self, mock_s3, app, node, user, enabled_addon):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node._id}/addons/s3/',
            {
                'data': {
                    'attributes': {
                        'access_token': 'test_access_key',
                        'secret_token': 'test_secret_key'
                    }
                },
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['external_account_id']
        assert resp.json['data']['attributes']['node_has_auth']

    @mock.patch('addons.s3.utils.S3Connection', return_value=_mock_s3_client())
    def test_addon_folders_PATCH(self, mock_s3, app, node_with_authorized_addon, user):
        resp = app.patch_json_api(
            f'/{API_BASE}nodes/{node_with_authorized_addon._id}/addons/s3/',
            {
                'data': {
                    'attributes': {
                        'folder_id': 'test_folder_id',
                        'folder_path': 'test_folder_path:/'
                    }
                },
            },
            auth=user.auth
        )
        assert resp.status_code == 200
        assert resp.json['data']['attributes']['folder_id'] == 'test_folder_id'
        assert resp.json['data']['attributes']['folder_path'] == 'test_folder_id (California)'
