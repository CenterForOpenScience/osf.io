import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory, DraftRegistrationFactory

from framework.auth import Auth
from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.weko.models import NodeSettings
from addons.weko.tests.factories import (
    WEKOUserSettingsFactory,
    WEKONodeSettingsFactory,
    WEKOAccountFactory
)
from addons.weko import client
from addons.weko.tests import utils


pytestmark = pytest.mark.django_db
fake_host = 'https://weko3.test.nii.ac.jp/weko/sword/'


def mock_requests_get(url, **kwargs):
    if url == 'https://weko3.test.nii.ac.jp/weko/api/tree':
        return utils.MockResponse(utils.fake_weko_indices, 200)
    if url == 'https://weko3.test.nii.ac.jp/weko/api/index/?search_type=2&q=100':
        return utils.MockResponse(utils.fake_weko_items, 200)
    if url == 'https://weko3.test.nii.ac.jp/weko/api/records/1000':
        return utils.MockResponse(utils.fake_weko_item, 200)
    return utils.mock_response_404

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'weko'
    full_name = 'WEKO'
    ExternalAccountFactory = WEKOAccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'weko'
    full_name = 'WEKO'
    ExternalAccountFactory = WEKOAccountFactory
    NodeSettingsFactory = WEKONodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = WEKOUserSettingsFactory

    def setUp(self):
        self.mock_requests_get = mock.patch('requests.get')
        self.mock_requests_get.side_effect = mock_requests_get
        self.mock_requests_get.start()
        self.mock_find_repository = mock.patch('addons.weko.provider.find_repository')
        self.mock_find_repository.return_value = {
            'host': fake_host,
            'client_id': None,
            'client_secret': None,
            'authorize_url': None,
            'access_token_url': None,
        }
        self.mock_find_repository.start()
        super(TestNodeSettings, self).setUp()

    def tearDown(self):
        self.mock_requests_get.stop()
        self.mock_find_repository.stop()
        super(TestNodeSettings, self).tearDown()

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'index_id': '1234567890',
            'owner': self.node
        }

    def test_before_register_no_settings(self):
        self.node_settings.user_settings = None
        message = self.node_settings.before_register(self.node, self.user)
        assert_false(message)

    def test_before_register_no_auth(self):
        self.node_settings.external_account = None
        message = self.node_settings.before_register(self.node, self.user)
        assert_false(message)

    def test_before_register_settings_and_auth(self):
        message = self.node_settings.before_register(self.node, self.user)
        assert_true(message)

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.node.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.user),
            draft_registration=DraftRegistrationFactory(branched_from=self.node),
        )
        assert_false(registration.has_addon('weko'))

    ## Overrides ##

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].oauth_key = 'key-17'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {
            'default_storage': {'storage': {}},
            'token': self.node_settings.external_account.oauth_key,
            'user_id': self.node_settings.external_account.provider_id.split(':')[1],
        }
        assert_equal(credentials, expected)

    def test_create_log(self):
        action = 'file_added'
        path = 'pizza.nii'
        nlog = self.node.logs.count()
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': path, 'materialized': path},
        )
        self.node.reload()
        assert_equal(self.node.logs.count(), nlog + 1)
        assert_equal(
            self.node.logs.latest().action,
            '{0}_{1}'.format(self.short_name, action),
        )
        assert_equal(
            self.node.logs.latest().params['filename'],
            path
        )

    def test_set_folder(self):
        index_id = '1234567890'
        with mock.patch.object(self.node_settings, 'create_client') as mock_create_client:
            mock_client = mock.MagicMock()
            mock_client.get_index_by_id.return_value = client.Index(None, dict(id=index_id, name='Test'))
            mock_create_client.return_value = mock_client
            self.node_settings.set_folder(
                index_id,
                auth=Auth(self.user),
            )
            assert_true(mock_client.get_index_by_id.called)
        self.node_settings.save()
        # Container was set
        assert_equal(self.node_settings.index_id, index_id)
        # Log was saved
        print(self.node.logs)
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_index_linked'.format(self.short_name))

    def test_serialize_settings(self):
        pass
