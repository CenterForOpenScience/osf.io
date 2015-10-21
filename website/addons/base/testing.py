# -*- coding: utf-8 -*-
import abc

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth

from website import settings
from website.addons.base import exceptions

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory, UserFactory
from tests.utils import patch_dynamic

class AddonTestCase(OsfTestCase):
    """General Addon TestCase that automatically sets up a user and node with
    an addon.

    Must define:

        - ADDON_SHORT_NAME (class variable)
        - set_user_settings(self, settings): Method that makes any modifications
            to the UserSettings object, e.g. setting access_token
        - set_node_settings(self, settings): Metehod that makes any modifications
            to the NodeSettings object.

    This will give you:

        - self.user: A User with the addon enabled
        - self.project: A project created by self.user and has the addon enabled
        - self.user_settings: AddonUserSettings object for the addon
        - self.node_settings: AddonNodeSettings object for the addon

    """
    DB_NAME = getattr(settings, 'TEST_DB_ADDON_NAME', 'osf_addon')
    ADDON_SHORT_NAME = None
    OWNERS = ['user', 'node']
    NODE_USER_FIELD = 'user_settings'

    # Optional overrides
    def create_user(self):
        return AuthUserFactory.build()

    def create_project(self):
        return ProjectFactory(creator=self.user)

    def set_user_settings(self, settings):
        """Make any necessary modifications to the user settings object,
        e.g. setting access_token.

        """
        raise NotImplementedError('Must define set_user_settings(self, settings) method')

    def set_node_settings(self, settings):
        raise NotImplementedError('Must define set_node_settings(self, settings) method')

    def create_user_settings(self):
        """Initialize user settings object if requested by `self.OWNERS`.

        """
        if 'user' not in self.OWNERS:
            return
        self.user.add_addon(self.ADDON_SHORT_NAME, override=True)
        assert self.user.has_addon(self.ADDON_SHORT_NAME), '{0} is not enabled'.format(self.ADDON_SHORT_NAME)
        self.user_settings = self.user.get_addon(self.ADDON_SHORT_NAME)
        self.set_user_settings(self.user_settings)
        self.user_settings.save()

    def create_node_settings(self):
        """Initialize node settings object if requested by `self.OWNERS`,
        additionally linking to user settings if requested by
        `self.NODE_USER_FIELD`.

        """
        if 'node' not in self.OWNERS:
            return
        self.project.add_addon(self.ADDON_SHORT_NAME, auth=Auth(self.user))
        self.node_settings = self.project.get_addon(self.ADDON_SHORT_NAME)
        # User has imported their addon settings to this node
        if self.NODE_USER_FIELD:
            setattr(self.node_settings, self.NODE_USER_FIELD, self.user_settings)
        self.set_node_settings(self.node_settings)
        self.node_settings.save()

    def setUp(self):

        super(AddonTestCase, self).setUp()

        self.user = self.create_user()
        if not self.ADDON_SHORT_NAME:
            raise ValueError('Must define ADDON_SHORT_NAME in the test class.')
        self.user.save()

        self.project = self.create_project()
        self.project.save()

        self.create_user_settings()
        self.create_node_settings()


class OAuthAddonTestSuiteBase(object):

    ___metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def short_name(self):
        pass

    @abc.abstractproperty
    def full_name(self):
        pass

    @abc.abstractproperty
    def ExternalAccountFactory(self):
        pass


class OAuthAddonUserSettingTestSuite(OAuthAddonTestSuiteBase):

    def setUp(self):
        super(OAuthAddonUserSettingTestSuite, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = self.ExternalAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon(self.short_name)

    def test_grant_oauth_access_no_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {self.node._id: {self.external_account._id: {}}},
        )

    def test_grant_oauth_access_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {
                self.node._id: {
                    self.external_account._id: {'folder': 'fake_folder_id'}
                },
            }
        )

    def test_verify_oauth_access_no_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.ExternalAccountFactory()
            )
        )

    def test_verify_oauth_access_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'folder': 'fake_folder_id'}
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'folder': 'another_folder_id'}
            )
        )

class OAuthAddonNodeSettingsTestSuite(OAuthAddonTestSuiteBase):

    @abc.abstractproperty
    def NodeSettingsFactory(self):
        pass

    @abc.abstractproperty
    def NodeSettingsClass(self):
        pass

    @abc.abstractproperty
    def UserSettingsFactory(self):
        pass

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '1234567890',
            'owner': self.node
        }

    def setUp(self):
        super(OAuthAddonNodeSettingsTestSuite, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = self.ExternalAccountFactory()

        self.user.add_addon(self.short_name)
        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_addon(self.short_name)
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        self.node_settings = self.NodeSettingsFactory(
            **self._node_settings_class_kwargs(self.node, self.user_settings)
        )
        self.node_settings.external_account = self.external_account
        self.node_settings.save()

    def tearDown(self):
        super(OAuthAddonNodeSettingsTestSuite, self).tearDown()
        self.user_settings.remove()
        self.node_settings.remove()
        self.external_account.remove()
        self.node.remove()
        self.user.remove()

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.user_settings.revoke_oauth_access(self.external_account)

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_fields(self):
        node_settings = self.NodeSettingsClass(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'provider_id'))
        assert_true(hasattr(node_settings, 'user_settings'))

    def test_folder_defaults_to_none(self):
        node_settings = self.NodeSettingsClass(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.provider_id)

    def test_has_auth(self):
        self.user.external_accounts = []
        self.user_settings.reload()
        settings = self.NodeSettingsClass(user_settings=self.user_settings)
        settings.save()
        assert_false(settings.has_auth)

        self.user.external_accounts.append(self.external_account)
        settings.reload()
        assert_true(settings.has_auth)

    def test_clear_auth(self):
        node_settings = self.NodeSettingsFactory()
        node_settings.external_account = self.ExternalAccountFactory()
        node_settings.user_settings = self.UserSettingsFactory()
        node_settings.save()

        node_settings.clear_auth()

        assert_is_none(node_settings.external_account)
        assert_is_none(node_settings.user_settings)

    def test_clear_settings(self):
        node_settings = self.NodeSettingsFactory()
        node_settings.external_account = self.ExternalAccountFactory()
        node_settings.user_settings = self.UserSettingsFactory()
        node_settings.save()

        node_settings.clear_settings()
        assert_is_none(node_settings.provider_id)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], self.short_name)

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.provider_id)
        old_logs = self.node.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.provider_id, None)
        assert_true(self.node_settings.deleted)
        assert_equal(self.node.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.provider_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.provider_id, None)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, '{0}_node_deauthorized'.format(self.short_name))
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)

    @patch_dynamic('NodeSettingsClass', '_update_folder_data')
    def test_set_folder(self, mock_update_folder):
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.provider_id, folder_id)
        # Log was saved
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_set_user_auth(self):
        node_settings = self.NodeSettingsFactory()
        user_settings = self.UserSettingsFactory()
        external_account = self.ExternalAccountFactory()

        user_settings.owner.external_accounts.append(external_account)
        user_settings.save()

        node_settings.external_account = external_account
        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, '{0}_node_authorized'.format(self.short_name))
        log_params = last_log.params
        assert_equal(log_params['node'], node_settings.owner._primary_key)
        assert_equal(last_log.user, user_settings.owner)

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'token': self.node_settings.external_account.oauth_key}
        assert_equal(credentials, expected)

    def test_serialize_credentials_not_authorized(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'folder': self.node_settings.provider_id}
        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()

    def test_create_log(self):
        action = 'file_added'
        path = 'pizza.nii'
        nlog = len(self.node.logs)
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': path, 'materialized': path},
        )
        self.node.reload()
        assert_equal(len(self.node.logs), nlog + 1)
        assert_equal(
            self.node.logs[-1].action,
            '{0}_{1}'.format(self.short_name, action),
        )
        assert_equal(
            self.node.logs[-1].params['path'],
            path
        )

    def test_after_fork_by_authorized_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.node, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_box_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone, message = self.node_settings.after_fork(
            node=self.node, fork=fork, user=user,
            save=True
        )
        assert_is(clone.user_settings, None)

    def test_before_fork(self):
        node = ProjectFactory()
        message = self.node_settings.before_fork(node, self.user)
        assert_true(message)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.node, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.node.project_or_component, message)

    def test_after_remove_authorized_box_user_not_self(self):
        message = self.node_settings.after_remove_contributor(
            self.node, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_after_remove_authorized_box_user_self(self):
        auth = Auth(user=self.user_settings.owner)
        message = self.node_settings.after_remove_contributor(
            self.node, self.user_settings.owner, auth)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_delete(self):
        self.node.remove_node(Auth(user=self.node.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.provider_id)
