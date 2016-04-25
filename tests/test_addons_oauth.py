import mock
from nose.tools import *

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from website import settings
from website.addons.base import AddonConfig
from website.addons.base import AddonOAuthNodeSettingsBase
from website.addons.base import AddonOAuthUserSettingsBase
from website.oauth.models import ExternalProvider

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from tests.factories import ExternalAccountFactory
from tests.factories import MockOAuth2Provider
from tests.factories import ProjectFactory

class MockConfig(AddonConfig):

    def __init__(self):
        super(MockConfig, self).__init__(
            short_name='mockaddon',
            full_name='Mock Addon',
            owners=[],
            categories=[]
        )

class MockNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = MockOAuth2Provider
    config = MockConfig()
    folder_id = 'foo'
    folder_name = 'Foo'
    folder_path = '/Foo'

    def deauthorize(*args, **kwargs):
        pass


class MockUserSettings(AddonOAuthUserSettingsBase):
    config = MockConfig
    oauth_provider = MockOAuth2Provider


class TestNodeSettings(OsfTestCase):

    ADDONS_UNDER_TEST = {
        MockOAuth2Provider.short_name: {
            'user_settings': MockUserSettings,
            'node_settings': MockNodeSettings,
        }
    }

    @classmethod
    def setUpClass(cls):
        super(TestNodeSettings, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNodeSettings, cls).tearDownClass()

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_or_add_addon(
            MockNodeSettings.oauth_provider.short_name,
            auth=Auth(user=self.user)
        )
        self.user_settings = self.user.get_or_add_addon(
            MockUserSettings.oauth_provider.short_name
        )
        self.external_account = ExternalAccountFactory()
        self.user.external_accounts.append(self.external_account)
        self.user.save()

    def test_has_auth_false(self):
        assert_false(self.node_settings.has_auth)

    def test_has_auth_no_grant(self):
        self.node_settings.external_account = self.external_account
        self.node_settings.user_settings = self.user_settings

        assert_false(self.node_settings.has_auth)

    def test_has_auth(self):
        self.node_settings.set_auth(
            external_account=self.external_account,
            user=self.user
        )

        assert_true(self.node_settings.has_auth)

    def test_set_auth(self):
        self.node_settings.set_auth(
            external_account=self.external_account,
            user=self.user
        )
        self.user_settings.reload()

        assert_equal(
            self.node_settings.external_account,
            self.external_account
        )
        assert_equal(
            self.node_settings.user_settings._id,
            self.user_settings._id
        )
        assert_in(
            self.project._id,
            self.user_settings.oauth_grants.keys()
        )

    @mock.patch('tests.test_addons_oauth.MockNodeSettings.deauthorize')
    @mock.patch('framework.auth.core._get_current_user')
    def test_revoke_auth(self, mock_decorator, mock_deauth):
        mock_decorator.return_value = self.user
        self.node_settings.set_auth(
            external_account=self.external_account,
            user=self.user
        )
        self.user_settings.reload()
        assert_equal(
            self.user_settings.oauth_grants,
            {self.project._id: {self.external_account._id: {}}}
        )

        self.user_settings.revoke_oauth_access(self.external_account, auth=Auth(self.user))
        self.user_settings.reload()

        assert_true(mock_deauth.called)
        assert_equal(
            self.user_settings.oauth_grants,
            {self.project._id: {}}
        )

    def test_clear_auth(self):
        self.node_settings.external_account = self.external_account
        self.node_settings.user_settings = self.user_settings

        self.node_settings.clear_auth()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.user_settings)


class TestUserSettings(OsfTestCase):

    ADDONS_UNDER_TEST = {
        MockOAuth2Provider.short_name: {
            'user_settings': MockUserSettings,
            'node_settings': MockNodeSettings,
        }
    }

    @classmethod
    def setUpClass(cls):
        super(TestUserSettings, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestUserSettings, cls).tearDownClass()

    def setUp(self):
        super(TestUserSettings, self).setUp()
        self.user = AuthUserFactory()

        self.user_settings = self.user.get_or_add_addon(
            MockUserSettings.oauth_provider.short_name
        )

        self.external_account = ExternalAccountFactory()
        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.project = ProjectFactory(creator=self.user)

    def tearDown(self):
        super(TestUserSettings, self).tearDown()

    def test_connected_accounts_empty(self):
        self.user.external_accounts = []

        assert_equal(
            self.user_settings.external_accounts,
            []
        )

    def test_connected_accounts(self):
        assert_equal(
            self.user_settings.external_accounts,
            [self.external_account]
        )

    def test_verify_false_no_grants(self):
        assert_false(
            self.user_settings.verify_oauth_access(
                external_account=self.external_account,
                node=self.project
            )
        )

    def test_verify_false_with_grants(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=ProjectFactory()
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                external_account=self.external_account,
                node=self.project
            )
        )

    def test_verify_false_metadata(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=self.project,
            metadata={'foo': 'bar'}
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                external_account=self.external_account,
                node=self.project,
                metadata={'baz': 'qiz'}
            )
        )

    def test_verify_true(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=self.project
        )

        assert_true(
            self.user_settings.verify_oauth_access(
                external_account=self.external_account,
                node=self.project
            )
        )

    def test_verify_true_with_metadata(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=self.project,
            metadata={'foo': 'bar'}
        )

        assert_true(
            self.user_settings.verify_oauth_access(
                external_account=self.external_account,
                node=self.project,
                metadata={'foo': 'bar'}
            )
        )

    def test_grant(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=self.project
        )

        assert_equal(
            self.user_settings.oauth_grants,
            {
                self.project._id: {
                    self.external_account._id: {}
                }
            }
        )

    def test_grant_not_owned(self):
        self.user.external_accounts = []

        with assert_raises(PermissionsError):
            self.user_settings.grant_oauth_access(
                external_account=self.external_account,
                node=self.project
            )

        assert_equal(
            self.user_settings.oauth_grants,
            {}
        )

    def test_grant_metadata(self):
        self.user_settings.grant_oauth_access(
            external_account=self.external_account,
            node=self.project,
            metadata={'foo': 'bar'}
        )

        assert_equal(
            self.user_settings.oauth_grants,
            {
                self.project._id: {
                    self.external_account._id: {'foo': 'bar'}
                }
            }
        )

    @mock.patch('tests.test_addons_oauth.MockUserSettings.revoke_remote_oauth_access')
    @mock.patch('framework.auth.core._get_current_user')
    def test_revoke_remote_access_called(self, mock_decorator, mock_revoke):
        mock_decorator.return_value = self.user
        self.user_settings.delete()
        assert_equal(mock_revoke.call_count, 1)

    @mock.patch('tests.test_addons_oauth.MockUserSettings.revoke_remote_oauth_access')
    @mock.patch('framework.auth.core._get_current_user')
    def test_revoke_remote_access_not_called(self, mock_decorator, mock_revoke):
        mock_decorator.return_value = self.user
        user2 = AuthUserFactory()
        user2.external_accounts.append(self.external_account)
        user2.save()
        self.user_settings.delete()
        assert_equal(mock_revoke.call_count, 0)

    def test_on_delete(self):
        node_settings = self.project.get_or_add_addon(
            MockUserSettings.oauth_provider.short_name,
            auth=Auth(user=self.user)
        )

        node_settings.set_auth(
            external_account=self.external_account,
            user=self.user
        )

        self.user.delete_addon(
            MockUserSettings.oauth_provider.short_name
        )

        node_settings.reload()

        assert_is_none(node_settings.external_account)
        assert_is_none(node_settings.user_settings)

