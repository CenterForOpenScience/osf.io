# -*- coding: utf-8 -*-

import mock
import unittest
from nose.tools import *  # noqa

from github3 import GitHubError
from github3.repos import Repository

from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import ExternalAccountFactory, ProjectFactory, UserFactory

from framework.auth import Auth

from website.addons.github.exceptions import NotFoundError
from website.addons.github import settings as github_settings
from website.addons.github.model import GitHubUserSettings
from website.addons.github.model import GitHubNodeSettings
from website.addons.github.tests.factories import (
    GitHubAccountFactory,
    GitHubNodeSettingsFactory,
    GitHubUserSettingsFactory
)
from website.addons.base.testing import models

from .utils import create_mock_github
mock_github = create_mock_github()


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'github'
    full_name = 'GitHub'
    ExternalAccountFactory = GitHubAccountFactory

    NodeSettingsFactory = GitHubNodeSettingsFactory
    NodeSettingsClass = GitHubNodeSettings
    UserSettingsFactory = GitHubUserSettingsFactory

    ## Mixin Overrides ##

    def test_set_folder(self):
        # GitHub doesn't use folderpicker, and the nodesettings model
        # does not need a `set_repo` method
        pass

    def test_serialize_settings(self):
        # GitHub's serialized_settings are a little different from 
        # common storage addons.
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'owner': self.node_settings.user, 'repo': self.node_settings.repo}
        assert_equal(settings, expected)

    @mock.patch(
        'website.addons.github.model.GitHubUserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super(TestNodeSettings, self).test_complete_has_auth_not_verified()

    @mock.patch('website.addons.github.api.GitHubClient.repos')
    @mock.patch('website.addons.github.api.GitHubClient.my_org_repos')
    def test_to_json(self, mock_org, mock_repos):
        mock_repos.return_value = {}
        mock_org.return_value = {}
        super(TestNodeSettings, self).test_to_json()

    @mock.patch('website.addons.github.api.GitHubClient.repos')
    @mock.patch('website.addons.github.api.GitHubClient.my_org_repos')
    def test_to_json_user_is_owner(self, mock_org, mock_repos):
        mock_repos.return_value = {}
        mock_org.return_value = {}
        result = self.node_settings.to_json(self.user)
        assert_true(result['user_has_auth'])
        assert_equal(result['github_user'], 'abc')
        assert_true(result['is_owner'])
        assert_true(result['valid_credentials'])
        assert_equal(result.get('repo_names', None), [])

    @mock.patch('website.addons.github.api.GitHubClient.repos')
    @mock.patch('website.addons.github.api.GitHubClient.my_org_repos')
    def test_to_json_user_is_not_owner(self, mock_org, mock_repos):
        mock_repos.return_value = {}
        mock_org.return_value = {}
        not_owner = UserFactory()
        result = self.node_settings.to_json(not_owner)
        assert_false(result['user_has_auth'])
        assert_equal(result['github_user'], 'abc')
        assert_false(result['is_owner'])
        assert_true(result['valid_credentials'])
        assert_equal(result.get('repo_names', None), None)


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'github'
    full_name = 'GitHub'
    ExternalAccountFactory = GitHubAccountFactory

    def test_public_id(self):
        assert_equal(self.user.external_accounts[0].display_name, self.user_settings.public_id)


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
        self.project.save()

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.external_account = GitHubAccountFactory()
        self.project.creator.external_accounts.append(self.external_account)
        self.project.creator.save()
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.external_account = self.external_account
        self.node_settings.save()
        self.node_settings.set_auth


    @mock.patch('website.addons.github.api.GitHubClient.repo')
    def test_before_make_public(self, mock_repo):
        mock_repo.side_effect = NotFoundError

        result = self.node_settings.before_make_public(self.project)
        assert_is(result, None)

    @mock.patch('website.addons.github.api.GitHubClient.repo')
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

    @mock.patch('website.addons.github.api.GitHubClient.repo')
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

    @mock.patch('website.addons.github.api.GitHubClient.repo')
    def test_before_page_load_osf_private_gh_public(self, mock_repo):
        mock_repo.return_value = Repository.from_json({'private': False})
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('website.addons.github.api.GitHubClient.repo')
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

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.project.creator),
            data='hodor',
        )
        assert_false(registration.has_addon('github'))



class TestGithubNodeSettings(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()
        self.user.add_addon('github')
        self.user_settings = self.user.get_addon('github')
        self.external_account = GitHubAccountFactory()
        self.user_settings.owner.external_accounts.append(self.external_account)
        self.user_settings.owner.save()
        self.node_settings = GitHubNodeSettingsFactory(user_settings=self.user_settings)

    @mock.patch('website.addons.github.api.GitHubClient.delete_hook')
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

    @mock.patch('website.addons.github.api.GitHubClient.delete_hook')
    def test_delete_hook_no_hook(self, mock_delete_hook):
        res = self.node_settings.delete_hook()
        assert_false(res)
        assert_false(mock_delete_hook.called)

    @mock.patch('website.addons.github.api.GitHubClient.delete_hook')
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

    @mock.patch('website.addons.github.api.GitHubClient.delete_hook')
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
