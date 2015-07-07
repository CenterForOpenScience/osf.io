# -*- coding: utf-8 -*-

import mock
import unittest
from nose.tools import *  # noqa

from github3 import GitHubError
from github3.repos import Repository

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory

from framework.auth import Auth

from website.addons.github.exceptions import NotFoundError
from website.addons.github import settings as github_settings
from website.addons.github.exceptions import TooBigToRenderError
from website.addons.github.tests.factories import GitHubOauthSettingsFactory
from website.addons.github.model import AddonGitHubUserSettings
from website.addons.github.model import AddonGitHubNodeSettings
from website.addons.github.model import AddonGitHubOauthSettings
from website.addons.github.model import GithubGuidFile

from .utils import create_mock_github
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

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.save()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

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

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert_true(message)

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_false(message)

    def test_after_remove_contributor_authenticator_self(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, self.consolidated_auth
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_remove_contributor_authenticator_not_self(self):
        auth = Auth(user=self.non_authenticator)
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, auth
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_after_remove_contributor_not_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.non_authenticator, self.consolidated_auth
        )
        assert_not_equal(
            self.node_settings.user_settings,
            None,
        )

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

    @mock.patch('website.archiver.tasks.archive.si')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=None,
            auth=Auth(user=self.project.creator),
            template='Template1',
            data='hodor'
        )
        assert_false(registration.has_addon('github'))


class TestAddonGithubUserSettings(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user_settings = AddonGitHubUserSettings()
        self.oauth_settings = AddonGitHubOauthSettings()
        self.oauth_settings.github_user_id = 'testuser'
        self.oauth_settings.save()
        self.user_settings.oauth_settings = self.oauth_settings
        self.user_settings.save()

    def test_repr(self):
        self.user_settings.owner = UserFactory()
        assert_in(self.user_settings.owner._id, repr(self.user_settings))
        oauth_settings = GitHubOauthSettingsFactory()

    def test_public_id_is_none_if_no_oauth_settings_attached(self):
        self.user_settings.oauth_settings = None
        self.user_settings.save()
        # Regression test for:
        #  https://github.com/CenterForOpenScience/openscienceframework.org/issues/1053
        assert_is_none(self.user_settings.public_id)

    def test_github_user_name(self):
        self.oauth_settings.github_user_name = "test user name"
        self.oauth_settings.save()
        assert_equal(self.user_settings.github_user_name, "test user name")

    def test_oauth_access_token(self):
        self.oauth_settings.oauth_access_token = "test access token"
        self.oauth_settings.save()
        assert_equal(self.user_settings.oauth_access_token, "test access token")

    def test_oauth_token_type(self):
        self.oauth_settings.oauth_token_type = "test token type"
        self.oauth_settings.save()
        assert_equal(self.user_settings.oauth_token_type, "test token type")

    @mock.patch('website.addons.github.api.GitHub.revoke_token')
    def test_clear_auth(self, mock_revoke_token):
        mock_revoke_token.return_value = True
        self.user_settings.clear_auth(save=True)
        assert_false(self.user_settings.github_user_name)
        assert_false(self.user_settings.oauth_token_type)
        assert_false(self.user_settings.oauth_access_token)
        assert_false(self.user_settings.oauth_settings)


class TestAddonGithubNodeSettings(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()
        self.user.add_addon('github')
        self.user_settings = self.user.get_addon('github')
        self.oauth_settings = AddonGitHubOauthSettings(oauth_access_token='foobar')
        self.oauth_settings.github_user_id = 'testuser'
        self.oauth_settings.save()
        self.user_settings.oauth_settings = self.oauth_settings
        self.user_settings.save()
        self.node_settings = AddonGitHubNodeSettings(
            owner=ProjectFactory(),
            user='chrisseto',
            repo='openpokemon',
            user_settings=self.user_settings,
        )
        self.node_settings.save()

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.node_settings.user = None

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_repo_false(self):
        self.node_settings.repo = None

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

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

    def test_to_json_noauthorizing_authed_user(self):
        user = UserFactory()
        user.add_addon('github')
        user_settings = user.get_addon('github')

        oauth_settings = AddonGitHubOauthSettings(oauth_access_token='foobar')
        oauth_settings.github_user_id = 'testuser'
        oauth_settings.save()

        user_settings.oauth_settings = self.oauth_settings
        user_settings.save()

        self.node_settings.to_json(user)
