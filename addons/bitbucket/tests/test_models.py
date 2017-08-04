# -*- coding: utf-8 -*-

import mock
import pytest
import unittest
from nose.tools import *  # noqa

from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ExternalAccountFactory, ProjectFactory, UserFactory

from framework.auth import Auth

from addons.bitbucket.exceptions import NotFoundError
from addons.bitbucket import settings as bitbucket_settings
from addons.bitbucket.models import NodeSettings
from addons.bitbucket.tests.factories import (
    BitbucketAccountFactory,
    BitbucketNodeSettingsFactory,
    BitbucketUserSettingsFactory
)
from addons.base.tests import models

pytestmark = pytest.mark.django_db


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'bitbucket'
    full_name = 'Bitbucket'
    ExternalAccountFactory = BitbucketAccountFactory

    NodeSettingsFactory = BitbucketNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = BitbucketUserSettingsFactory

    ## Mixin Overrides ##

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }

    def test_set_folder(self):
        # Bitbucket doesn't use folderpicker, and the nodesettings model
        # does not need a `set_repo` method
        pass

    def test_serialize_settings(self):
        # Bitbucket's serialized_settings are a little different from 
        # common storage addons.
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'owner': self.node_settings.user, 'repo': self.node_settings.repo}
        assert_equal(settings, expected)

    @mock.patch(
        'addons.bitbucket.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super(TestNodeSettings, self).test_complete_has_auth_not_verified()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        super(TestNodeSettings, self).test_to_json()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json_user_is_owner(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        result = self.node_settings.to_json(self.user)
        assert_true(result['user_has_auth'])
        assert_equal(result['bitbucket_user'], 'abc')
        assert_true(result['is_owner'])
        assert_true(result['valid_credentials'])
        assert_equal(result.get('repo_names', None), [])

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json_user_is_not_owner(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        not_owner = UserFactory()
        result = self.node_settings.to_json(not_owner)
        assert_false(result['user_has_auth'])
        assert_equal(result['bitbucket_user'], 'abc')
        assert_false(result['is_owner'])
        assert_true(result['valid_credentials'])
        assert_equal(result.get('repo_names', None), None)


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'bitbucket'
    full_name = 'Bitbucket'
    ExternalAccountFactory = BitbucketAccountFactory

    def test_public_id(self):
        assert_equal(self.user.external_accounts.first().display_name, self.user_settings.public_id)


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(self.project.creator)
        self.project.creator.save()
        self.non_authenticator = UserFactory()
        self.non_authenticator.save()
        self.project.save()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )

        self.project.add_addon('bitbucket', auth=self.consolidated_auth)
        self.project.creator.add_addon('bitbucket')
        self.external_account = BitbucketAccountFactory()
        self.project.creator.external_accounts.add(self.external_account)
        self.project.creator.save()
        self.node_settings = self.project.get_addon('bitbucket')
        self.user_settings = self.project.creator.get_addon('bitbucket')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.external_account = self.external_account
        self.node_settings.save()
        self.node_settings.set_auth
        self.user_settings.oauth_grants[self.project._id] = {self.external_account._id: []}
        self.user_settings.save()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_make_public(self, mock_repo):
        mock_repo.side_effect = NotFoundError

        result = self.node_settings.before_make_public(self.project)
        assert_is(result, None)

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_public_bb_public(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = {'is_private': False}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert_false(message)

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_public_bb_private(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = {'is_private': True}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_private_bb_public(self, mock_repo):
        mock_repo.return_value = {'is_private': False}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert_true(message)

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_private_bb_private(self, mock_repo):
        mock_repo.return_value = {'is_private': True}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
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
        clone = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert_equal(
            self.node_settings.user_settings,
            clone.user_settings,
        )

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
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
        assert_false(registration.has_addon('bitbucket'))
