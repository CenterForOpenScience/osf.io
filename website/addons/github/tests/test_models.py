# -*- coding: utf-8 -*-

import mock
import unittest
from nose.tools import *  # noqa

from framework.exceptions import PermissionsError
from github3 import GitHubError
from github3.repos import Repository

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory, AuthUserFactory

from framework.auth import Auth

from website.addons.github.exceptions import NotFoundError
from website.addons.github import settings as github_settings
from website.addons.github.exceptions import TooBigToRenderError
from website.addons.github.model import GitHubUserSettings
from website.addons.github.model import GitHubNodeSettings
from website.addons.github.model import GithubGuidFile
from website.addons.github.tests.utils import create_mock_github
from website.addons.github.tests.factories import (
    GitHubAccountFactory,
    GitHubUserSettingsFactory,
    ExternalAccountFactory,
)
from website.addons.github import model

mock_github = create_mock_github()


class TestFileGuid(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('github', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('github')

    def test_provider(self):
        assert_equal('github', GithubGuidFile().provider)

    def test_correct_path(self):
        guid, _ = self.node_addon.find_or_create_file_guid('perth')
        assert_equal(guid.waterbutler_path, 'perth')
        assert_equal(guid.waterbutler_path, guid.path)

    def test_extra_without_metadata(self):
        guid, _ = self.node_addon.find_or_create_file_guid('perth')

        assert_equal(guid.extra, {})

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'fileSha': 'Im a little tea pot'
                }
            }
        }

        guid, _ = self.node_addon.find_or_create_file_guid('perth')
        guid.enrich()

        assert_equal(guid.unique_identifier, 'Im a little tea pot')

    def test_exception_from_response(self):
        mock_response = mock.Mock()
        mock_response.json.return_value = {'errors': [{'code': 'too_large'}]}

        guid, _ = self.node_addon.find_or_create_file_guid('perth')

        with assert_raises(TooBigToRenderError):
            guid._exception_from_response(mock_response)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('/4/2')

        assert_true(created)
        assert_equal(guid.waterbutler_path, '/4/2')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()
        self.project = ProjectFactory()
        self.node_settings = model.GitHubNodeSettings(owner=self.project)
        self.node_settings.save()
        self.external_account = ExternalAccountFactory()

        self.user = self.project.creator
        self.user.external_accounts.append(self.external_account)
        self.user.save()
        self.user_settings = self.user.get_or_add_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()
        self.user_settings.save()
        self.non_authenticator = UserFactory()
        self.consolidated_auth = Auth(self.project.creator)
        self.project.add_contributor(
             contributor=self.non_authenticator,
             auth=self.consolidated_auth,
        )
        self.project.save()


    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_make_public(self, mock_repo):
        mock_repo.side_effect = NotFoundError

        result = self.node_settings.before_make_public(self.project)
        assert_is(result, None)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_public_gh_public(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = Repository.from_json({'private': False})
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_false(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_public_gh_private(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = Repository.from_json({'private': True})
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_private_gh_public(self, mock_repo):
        mock_repo.return_value = Repository.from_json({'private': False})
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_before_page_load_osf_private_gh_private(self, mock_repo):
        mock_repo.return_value = Repository.from_json({'private': True})
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_false(message)

    def test_before_page_load_not_contributor(self):
        message = self.node_settings.before_page_load(self.project, UserFactory())
        assert_false(message)

    def test_before_page_load_not_logged_in(self):
        message = self.node_settings.before_page_load(self.project, None)
        assert_false(message)


    @unittest.skipIf(not github_settings.SET_PRIVACY, 'Setting privacy is disabled.')
    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_privacy_private_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_privacy(
            self.project, 'private',
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            True,
        )
        assert_true(message)
        assert_in('made private', message.lower())

    @unittest.skipIf(not github_settings.SET_PRIVACY, 'Setting privacy is disabled.')
    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_privacy_public_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_privacy(
            self.project, 'public'
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            False,
        )
        assert_true(message)
        assert_in('made public', message.lower())

    @unittest.skipIf(not github_settings.SET_PRIVACY, 'Setting privacy is disabled.')
    @mock.patch('website.addons.github.api.GitHub.repo')
    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_privacy_not_authenticated(self, mock_set_privacy, mock_repo):
        mock_set_privacy.return_value = {'errors': ['it broke']}
        mock_repo.return_value = {'private': True}
        message = self.node_settings.after_set_privacy(
            self.project, 'private',
        )
        mock_set_privacy.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
            True,
        )
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)
        assert_in('could not set privacy', message.lower())

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert_equal(
            self.node_settings.user_settings,
            clone.user_settings,
        )

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert_equal(
            clone.user_settings,
            None,
        )

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)

    def test_does_not_get_copied_to_registrations(self):
        registration = self.project.register_node(
            schema=None,
            auth=Auth(user=self.project.creator),
            template='Template1',
            data='hodor'
        )
        assert_false(registration.has_addon('github'))


class TestGithubUserSettings(OsfTestCase):

    def _prep_oauth_case(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = ExternalAccountFactory()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('github')
        print "debug"

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
            metadata={'repo': 'fake_repo_id'}
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {
                self.node._id: {
                    self.external_account._id: {'repo': 'fake_repo_id'}
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
                external_account=ExternalAccountFactory()
            )
        )

    def test_verify_oauth_access_metadata(self):
        self._prep_oauth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'repo': 'fake_repo_id'}
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'repo': 'fake_repo_id'}
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'repo': 'another_repo_id'}
            )
        )



class GitHubNodeSettingsTestCase(OsfTestCase):

    def setUp(self):
        super(GitHubNodeSettingsTestCase, self).setUp()
        self.node = ProjectFactory()
        self.node_settings = model.GitHubNodeSettings(owner=self.node)
        self.node_settings.save()
        self.user = self.node.creator
        self.user_settings = self.user.get_or_add_addon('github')
        self.node_settings.user_settings = self.user_settings



    def tearDown(self):
        super(GitHubNodeSettingsTestCase, self).tearDown()
        self.user_settings.remove()
        self.node_settings.remove()
        self.node.remove()
        self.user.remove()

    @mock.patch('website.addons.github.model.GitHubProvider')
    def test_api_not_cached(self, mock_github):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_github.assert_called_once()
        assert_equal(api, mock_github())

    @mock.patch('website.addons.github.model.GitHubProvider')
    def test_api_cached(self, mock_github):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_github.called)
        assert_equal(api, 'testapi')

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_set_auth(self, mock_repo):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user
        )

        # this instance is updated
        assert_equal(
            self.node_settings.external_account,
            external_account
        )
        assert_equal(
            self.node_settings.user_settings,
            self.user_settings
        )

    def test_set_auth_wrong_user(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.user.save()

        with assert_raises(PermissionsError):
            self.node_settings.set_auth(
                external_account=external_account,
                user=UserFactory()
            )

    def test_clear_auth(self):
        self.node_settings.external_account = ExternalAccountFactory()
        self.node_settings.repo = 'something'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

        self.node_settings.clear_auth()

        assert_is_none(self.node_settings.external_account)
        assert_is_none(self.node_settings.repo)
        assert_is_none(self.node_settings.user_settings)


    def test_has_auth_false(self):
        external_account = ExternalAccountFactory()

        assert_false(self.node_settings.has_auth)

        # both external_account and user_settings must be set to have auth
        self.node_settings.external_account = external_account
        assert_false(self.node_settings.has_auth)

        self.node_settings.external_account = None
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)

        # set_auth must be called to have auth
        self.node_settings.external_account = external_account
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)


    def test_has_auth_true(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)

        self.node_settings.set_auth(external_account, self.user)

        # mendeley_list_id should have no effect
        self.node_settings.mendeley_list_id = None
        assert_true(self.node_settings.has_auth)

        # mendeley_list_id should have no effect
        self.node_settings.mendeley_list_id = 'totally fake ID'
        assert_true(self.node_settings.has_auth)

    # failing
    @mock.patch('framework.status.push_status_message')
    def test_remove_contributor_authorizer(self, mock_push_status):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)

        contributor = UserFactory()
        self.node.add_contributor(contributor)
        self.node.remove_contributor(self.node.creator, auth=Auth(user=contributor))

        assert_false(self.node_settings.has_auth)
        assert_false(self.user_settings.verify_oauth_access(self.node, external_account))

    def test_remove_contributor_not_authorizer(self):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)

        contributor = UserFactory()
        self.node.add_contributor(contributor)
        self.node.remove_contributor(contributor, auth=Auth(user=self.node.creator))

        assert_true(self.node_settings.has_auth)
        assert_true(self.user_settings.verify_oauth_access(self.node, external_account))

    @mock.patch('framework.status.push_status_message')
    def test_fork_by_authorizer(self, mock_push_status):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)

        fork = self.node.fork_node(auth=Auth(user=self.node.creator))

        assert_true(fork.get_addon('github').has_auth)
        assert_true(self.user_settings.verify_oauth_access(fork, external_account))

    @mock.patch('framework.status.push_status_message')
    def test_fork_not_by_authorizer(self, mock_push_status):
        external_account = ExternalAccountFactory()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)

        contributor = UserFactory()
        self.node.add_contributor(contributor)
        fork = self.node.fork_node(auth=Auth(user=contributor))

        assert_false(fork.get_addon('github').has_auth)
        assert_false(self.user_settings.verify_oauth_access(fork, external_account))


    @mock.patch('website.addons.github.api.GitHub.delete_hook')
    def test_delete_hook(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert_true(res)
        mock_delete_hook.assert_called_with(*args)

    @mock.patch('website.addons.github.api.GitHub.delete_hook')
    def test_delete_hook_no_hook(self, mock_delete_hook):
        res = self.node_settings.delete_hook()
        assert_false(res)
        assert_false(mock_delete_hook.called)

    # running test again
    @mock.patch('website.addons.github.api.GitHub.delete_hook')
    def test_delete_hook_not_found(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        mock_delete_hook.side_effect = NotFoundError
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert_false(res)
        mock_delete_hook.assert_called_with(*args)

    @mock.patch('website.addons.github.api.GitHub.delete_hook')
    def test_delete_hook_error(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        mock_delete_hook.side_effect = GitHubError(mock.Mock())
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert_false(res)
        mock_delete_hook.assert_called_with(*args)