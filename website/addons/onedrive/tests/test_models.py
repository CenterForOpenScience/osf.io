# -*- coding: utf-8 -*-
import mock

from nose.tools import *  # noqa (PEP8 asserts)
from box import BoxClientException

from framework.auth import Auth
from framework.exceptions import HTTPError
from website.addons.box.model import (
    BoxUserSettings, BoxNodeSettings
)
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.box.tests.factories import (
    BoxAccountFactory,
    BoxUserSettingsFactory,
    BoxNodeSettingsFactory,
)
from website.addons.base import exceptions


class TestUserSettingsModel(OsfTestCase):

    def _prep_oauth_case(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = BoxAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('box')

    def test_grant_oauth_access_no_metadata(self):
        self._prep_oauth_case()

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
        self._prep_oauth_case()

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
        self._prep_oauth_case()

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
                external_account=BoxAccountFactory()
            )
        )

    def test_verify_oauth_access_metadata(self):
        self._prep_oauth_case()

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


class TestBoxNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestBoxNodeSettingsModel, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = BoxAccountFactory()

        self.user.add_addon('box')
        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_addon('box')
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        self.node_settings = BoxNodeSettingsFactory(
            user_settings=self.user_settings,
            folder_id='1234567890',
            owner=self.node
        )
        self.node_settings.external_account = self.external_account
        self.node_settings.save()

    def tearDown(self):
        super(TestBoxNodeSettingsModel, self).tearDown()
        self.user_settings.remove()
        self.node_settings.remove()
        self.external_account.remove()
        self.node.remove()
        self.user.remove()

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.user_settings.oauth_grants[self.node._id].pop(self.external_account._id)

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_fields(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'folder_id'))
        assert_true(hasattr(node_settings, 'user_settings'))

    def test_folder_defaults_to_none(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    def test_has_auth(self):
        self.user.external_accounts = []
        self.user_settings.reload()
        settings = BoxNodeSettings(user_settings=self.user_settings)
        settings.save()
        assert_false(settings.has_auth)

        self.user.external_accounts.append(self.external_account)
        settings.reload()
        assert_true(settings.has_auth)

    def test_clear_auth(self):
        node_settings = BoxNodeSettingsFactory()
        node_settings.external_account = BoxAccountFactory()
        node_settings.user_settings = BoxUserSettingsFactory()
        node_settings.save()

        node_settings.clear_auth()

        assert_is_none(node_settings.external_account)
        assert_is_none(node_settings.folder_id)
        assert_is_none(node_settings.user_settings)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'box')

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        old_logs = self.node.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)
        assert_true(self.node_settings.deleted)
        assert_equal(self.node.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)
        assert_in('folder_id', params)

    @mock.patch("website.addons.box.model.BoxNodeSettings._update_folder_data")
    def test_set_folder(self, mock_update_folder):
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, 'box_folder_selected')

    def test_set_user_auth(self):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()
        external_account = BoxAccountFactory()

        user_settings.owner.external_accounts.append(external_account)
        user_settings.save()

        node_settings.external_account = external_account
        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, 'box_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['folder_id'], node_settings.folder_id)
        assert_equal(log_params['node'], node_settings.owner._primary_key)
        assert_equal(last_log.user, user_settings.owner)

    @mock.patch("website.addons.box.model.refresh_oauth_key")
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        self.user_settings.access_token = 'key-11'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'token': self.node_settings.user_settings.access_token}

        assert_equal(credentials, expected)

    def test_serialize_credentials_not_authorized(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'folder': self.node_settings.folder_id}
        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.folder_id = None
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
            'box_{0}'.format(action),
        )
        assert_equal(
            self.node.logs[-1].params['path'],
            path
        )


class TestNodeSettingsCallbacks(OsfTestCase):

    def setUp(self):
        super(TestNodeSettingsCallbacks, self).setUp()
        # Create node settings with auth
        self.user_settings = BoxUserSettingsFactory(access_token='123abc')
        self.node_settings = BoxNodeSettingsFactory(
            user_settings=self.user_settings,
        )
        self.external_account = BoxAccountFactory()
        self.user_settings.owner.external_accounts.append(self.external_account)
        self.node_settings.external_account = self.external_account

        self.project = self.node_settings.owner
        self.user = self.user_settings.owner

        self.user_settings.grant_oauth_access(
            node=self.project,
            external_account=self.external_account,
        )

    def test_after_fork_by_authorized_box_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        print(message)
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_box_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=user,
            save=True
        )
        # need request context for url_for
        assert_is(clone.user_settings, None)

    def test_before_fork(self):
        node = ProjectFactory()
        message = self.node_settings.before_fork(node, self.user)
        assert_true(message)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.project.project_or_component, message)

    def test_after_remove_authorized_box_user_not_self(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_after_remove_authorized_box_user_self(self):
        auth = Auth(user=self.user_settings.owner)
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner, auth)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.folder_id)
