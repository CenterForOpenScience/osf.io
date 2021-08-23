import abc

import mock
import pytest
import pytz
import datetime
from addons.base.tests.utils import MockFolder
from django.utils import timezone
from framework.auth import Auth
from framework.exceptions import HTTPError
from nose.tools import (assert_equal, assert_false, assert_in, assert_is,
                        assert_is_none, assert_not_in, assert_raises,
                        assert_true)
from osf.utils.permissions import ADMIN
from osf_tests.factories import ProjectFactory, UserFactory
from tests.utils import mock_auth
from addons.base import exceptions
from osf_tests.conftest import request_context

pytestmark = pytest.mark.django_db


class OAuthAddonModelTestSuiteMixinBase(object):

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


@pytest.mark.enable_quickfiles_creation
class OAuthAddonUserSettingTestSuiteMixin(OAuthAddonModelTestSuiteMixinBase):

    def setUp(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = self.ExternalAccountFactory()

        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon(self.short_name)

    def test_mergability(self):
        assert self.user_settings.can_be_merged

    def test_merge_user_settings(self):
        other_node = ProjectFactory()
        other_user = other_node.creator
        other_account = self.ExternalAccountFactory()
        other_user.external_accounts.add(other_account)
        other_user_settings = other_user.get_or_add_addon(self.short_name)
        other_node_settings = other_node.get_or_add_addon(self.short_name, auth=Auth(other_user))
        other_node_settings.set_auth(
            user=other_user,
            external_account=other_account
        )

        assert other_node_settings.has_auth
        assert other_node._id not in self.user_settings.oauth_grants
        assert other_node_settings.user_settings == other_user_settings

        self.user.merge_user(other_user)
        self.user.save()

        other_node_settings.reload()
        self.user_settings.reload()

        assert other_node_settings.has_auth
        assert other_node._id in self.user_settings.oauth_grants
        assert other_node_settings.user_settings == self.user_settings

    def test_grant_oauth_access_no_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert self.user_settings.oauth_grants == {self.node._id: {self.external_account._id: {}}}

    def test_grant_oauth_access_metadata(self):
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

        assert self.user_settings.oauth_grants == {
            self.node._id: {
                self.external_account._id: {'folder': 'fake_folder_id'}
            },
        }

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

class OAuthAddonNodeSettingsTestSuiteMixin(OAuthAddonModelTestSuiteMixinBase):

    @pytest.yield_fixture(autouse=True)
    def _request_context(self, app):
        context = app.test_request_context(headers={
            'Remote-Addr': '146.9.219.56',
            'User-Agent': 'Mozilla/5.0 (X11; U; SunOS sun4u; en-US; rv:0.9.4.1) Gecko/20020518 Netscape6/6.2.3'
        })
        context.push()
        yield context
        context.pop()

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
        super(OAuthAddonNodeSettingsTestSuiteMixin, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = self.ExternalAccountFactory()

        self.user.add_addon(self.short_name)
        self.user.external_accounts.add(self.external_account)

        self.user_settings = self.user.get_addon(self.short_name)
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': '1234567890'}
        )
        self.user_settings.save()

        self.node_settings = self.NodeSettingsFactory(
            external_account=self.external_account,
            **self._node_settings_class_kwargs(self.node, self.user_settings)
        )

    @pytest.mark.django_db
    def test_configured_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)
        assert_true(self.node_settings.configured)

    def test_configured_false(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        assert_false(self.node_settings.configured)

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_has_auth_not_verified(self):
        with mock_auth(self.user):
            self.user_settings.revoke_oauth_access(self.external_account)

        self.node_settings.reload()
        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)
        assert_equal(
            self.user_settings.oauth_grants,
            {self.node._id: {}}
        )

    def test_revoke_remote_access_called(self):

        with mock.patch.object(self.user_settings, 'revoke_remote_oauth_access') as mock_revoke:
            with mock_auth(self.user):
                self.user_settings.revoke_oauth_access(self.external_account)
        assert_equal(mock_revoke.call_count, 1)

    def test_revoke_remote_access_not_called(self):
        user2 = UserFactory()
        user2.external_accounts.add(self.external_account)
        user2.save()
        with mock.patch.object(self.user_settings, 'revoke_remote_oauth_access') as mock_revoke:
            with mock_auth(self.user):
                self.user_settings.revoke_oauth_access(self.external_account)
        assert_equal(mock_revoke.call_count, 0)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_fields(self):
        node_settings = self.NodeSettingsClass(owner=ProjectFactory(), user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'folder_id'))
        assert_true(hasattr(node_settings, 'user_settings'))

    def test_folder_defaults_to_none(self):
        node_settings = self.NodeSettingsClass(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    def test_has_auth(self):
        self.user.external_accounts.clear()
        self.user_settings.reload()
        node = ProjectFactory()
        settings = self.NodeSettingsClass(user_settings=self.user_settings, owner=node)
        settings.save()
        assert_false(settings.has_auth)

        self.user.external_accounts.add(self.external_account)
        settings.set_auth(self.external_account, self.user)
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
        assert_is_none(node_settings.folder_id)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], self.short_name)

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        old_logs = list(self.node.logs.all())
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)
        assert_true(self.node_settings.is_deleted)
        assert_equal(self.node_settings.deleted, mock_now)
        assert_equal(list(self.node.logs.all()), list(old_logs))

    def test_on_delete(self):
        self.user.delete_addon(
            self.user_settings.oauth_provider.short_name
        )

        self.node_settings.reload()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.user_settings)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        last_log = self.node.logs.first()
        assert_equal(last_log.action, '{0}_node_deauthorized'.format(self.short_name))
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)

    def test_set_folder(self):
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs.first()
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_set_user_auth(self):
        node_settings = self.NodeSettingsFactory()
        user_settings = self.UserSettingsFactory()
        external_account = self.ExternalAccountFactory()

        user_settings.owner.external_accounts.add(external_account)
        user_settings.save()

        node_settings.external_account = external_account
        node_settings.set_auth(external_account, user_settings.owner)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs.first()
        assert_equal(last_log.action, '{0}_node_authorized'.format(self.short_name))
        log_params = last_log.params
        assert_equal(log_params['node'], node_settings.owner._id)
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
        expected = {'folder': self.node_settings.folder_id}
        assert_equal(settings, expected)

    def test_serialize_settings_not_configured(self):
        self.node_settings.clear_settings()
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_settings()

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
            self.node.logs.latest().params['path'],
            path
        )

    def test_after_fork_by_authorized_user(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
            node=self.node, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone = self.node_settings.after_fork(
            node=self.node, fork=fork, user=user,
            save=True
        )
        assert_is(clone.user_settings, None)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.node, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.node.project_or_component, message)

    def test_after_remove_authorized_user_not_self(self):
        message = self.node_settings.after_remove_contributor(
            self.node, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_in('You can re-authenticate', message)

    def test_after_remove_authorized_user_self(self):
        auth = Auth(user=self.user_settings.owner)
        message = self.node_settings.after_remove_contributor(
            self.node, self.user_settings.owner, auth)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_not_in('You can re-authenticate', message)

    def test_after_delete(self):
        self.node.remove_node(Auth(user=self.node.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.folder_id)


class OAuthCitationsTestSuiteMixinBase(OAuthAddonModelTestSuiteMixinBase):
    @abc.abstractproperty
    def ProviderClass(self):
        pass

    @abc.abstractproperty
    def OAuthProviderClass(self):
        pass


class OAuthCitationsNodeSettingsTestSuiteMixin(
        OAuthAddonNodeSettingsTestSuiteMixin,
        OAuthCitationsTestSuiteMixinBase):

    def setUp(self):
        super(OAuthCitationsNodeSettingsTestSuiteMixin, self).setUp()
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id'}
        )
        self.user_settings.save()

    def test_fetch_folder_name_root(self):
        self.node_settings.list_id = 'ROOT'

        assert_equal(
            self.node_settings.fetch_folder_name,
            'All Documents'
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.list_id = None

        assert_equal(
            self.node_settings.fetch_folder_name,
            ''
        )

    def test_selected_folder_name(self):
        # Mock the return from api call to get the folder's name
        mock_folder = MockFolder()
        name = None

        with mock.patch.object(self.OAuthProviderClass, '_folder_metadata', return_value=mock_folder):
            name = self.node_settings.fetch_folder_name

        assert_equal(
            name,
            'Fake Folder'
        )

    def test_api_not_cached(self):
        # The first call to .api returns a new object
        with mock.patch.object(self.NodeSettingsClass, 'oauth_provider') as mock_api:
            api = self.node_settings.api
            mock_api.assert_called_once_with(account=self.external_account)
            assert_equal(api, mock_api())

    def test_api_cached(self):
        # Repeated calls to .api returns the same object
        with mock.patch.object(self.NodeSettingsClass, 'oauth_provider') as mock_api:
            self.node_settings._api = 'testapi'
            api = self.node_settings.api
            assert_false(mock_api.called)
            assert_equal(api, 'testapi')

    ############# Overrides ##############
    # `pass` due to lack of waterbutler- #
    # related events for citation addons #
    ######################################

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'owner': self.node
        }

    def test_serialize_credentials(self):
        pass

    def test_serialize_credentials_not_authorized(self):
        pass

    def test_serialize_settings(self):
        pass

    def test_serialize_settings_not_configured(self):
        pass

    def test_create_log(self):
        pass

    def test_set_folder(self):
        folder_id = 'fake-folder-id'
        folder_name = 'fake-folder-name'

        self.node_settings.clear_settings()
        self.node_settings.save()
        assert_is_none(self.node_settings.list_id)

        provider = self.ProviderClass()

        provider.set_config(
            self.node_settings,
            self.user,
            folder_id,
            folder_name,
            auth=Auth(user=self.user),
        )

        # instance was updated
        assert_equal(
            self.node_settings.list_id,
            'fake-folder-id',
        )

        # user_settings was updated
        # TODO: the call to grant_oauth_access should be mocked
        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'folder': 'fake-folder-id'}
            )
        )

        log = self.node.logs.latest()
        assert_equal(log.action, '{}_folder_selected'.format(self.short_name))
        assert_equal(log.params['folder_id'], folder_id)
        assert_equal(log.params['folder_name'], folder_name)

    @mock.patch('framework.status.push_status_message')
    def test_remove_contributor_authorizer(self, mock_push_status):
        contributor = UserFactory()
        self.node.add_contributor(contributor, permissions=ADMIN)
        self.node.remove_contributor(self.node.creator, auth=Auth(user=contributor))
        self.node_settings.reload()
        self.user_settings.reload()
        assert_false(self.node_settings.has_auth)
        assert_false(self.user_settings.verify_oauth_access(self.node, self.external_account))

    def test_remove_contributor_not_authorizer(self):
        contributor = UserFactory()
        self.node.add_contributor(contributor)
        self.node.remove_contributor(contributor, auth=Auth(user=self.node.creator))

        assert_true(self.node_settings.has_auth)
        assert_true(self.user_settings.verify_oauth_access(self.node, self.external_account))

    @mock.patch('framework.status.push_status_message')
    def test_fork_by_authorizer(self, mock_push_status):
        fork = self.node.fork_node(auth=Auth(user=self.node.creator))

        self.user_settings.reload()
        assert_true(fork.get_addon(self.short_name).has_auth)
        assert_true(self.user_settings.verify_oauth_access(fork, self.external_account))

    @mock.patch('framework.status.push_status_message')
    def test_fork_not_by_authorizer(self, mock_push_status):
        contributor = UserFactory()
        self.node.add_contributor(contributor)
        fork = self.node.fork_node(auth=Auth(user=contributor))

        assert_false(fork.get_addon(self.short_name).has_auth)
        assert_false(self.user_settings.verify_oauth_access(fork, self.external_account))

class CitationAddonProviderTestSuiteMixin(OAuthCitationsTestSuiteMixinBase):

    @abc.abstractproperty
    def ApiExceptionClass(self):
        pass

    def setUp(self):
        super(CitationAddonProviderTestSuiteMixin, self).setUp()
        self.provider = self.OAuthProviderClass()

    @abc.abstractmethod
    def test_handle_callback(self):
        pass

    def test_citation_lists(self):
        mock_client = mock.Mock()
        mock_folders = [MockFolder()]
        mock_list = mock.Mock()
        mock_list.items = mock_folders
        mock_client.folders.list.return_value = mock_list
        mock_client.collections.return_value = mock_folders
        self.provider._client = mock_client
        mock_account = mock.Mock()
        self.provider.account = mock_account
        res = self.provider.citation_lists(self.ProviderClass()._extract_folder)
        assert_equal(res[1]['name'], mock_folders[0].name)
        assert_equal(res[1]['id'], mock_folders[0].json['id'])

    def test_client_not_cached(self):
        # The first call to .client returns a new client
        with mock.patch.object(self.OAuthProviderClass, '_get_client') as mock_get_client:
            mock_account = mock.Mock()
            mock_account.expires_at = timezone.now()
            self.provider.account = mock_account
            self.provider.client
            mock_get_client.assert_called_with()
            assert_true(mock_get_client.called)

    def test_client_cached(self):
        # Repeated calls to .client returns the same client
        with mock.patch.object(self.OAuthProviderClass, '_get_client') as mock_get_client:
            self.provider._client = mock.Mock()
            res = self.provider.client
            assert_equal(res, self.provider._client)
            assert_false(mock_get_client.called)

    def test_has_access(self):
        with mock.patch.object(self.OAuthProviderClass, '_get_client') as mock_get_client:
            mock_client = mock.Mock()
            mock_error = mock.PropertyMock()
            mock_error.status_code = 403
            mock_error.text = 'Mocked 403 ApiException'
            mock_client.folders.list.side_effect = self.ApiExceptionClass(mock_error)
            mock_client.collections.side_effect = self.ApiExceptionClass(mock_error)
            mock_get_client.return_value = mock_client
            with assert_raises(HTTPError) as exc_info:
                self.provider.client
            assert_equal(exc_info.exception.code, 403)
