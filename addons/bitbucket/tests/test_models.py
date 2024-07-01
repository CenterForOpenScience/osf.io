from unittest import mock
import pytest
import unittest

from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import (
    ExternalAccountFactory,
    ProjectFactory,
    UserFactory,
    DraftRegistrationFactory,
)

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
        assert settings == expected

    @mock.patch(
        'addons.bitbucket.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super().test_complete_has_auth_not_verified()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        super().test_to_json()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json_user_is_owner(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        result = self.node_settings.to_json(self.user)
        assert result['user_has_auth']
        assert result['bitbucket_user'] == 'abc'
        assert result['is_owner']
        assert result['valid_credentials']
        assert result.get('repo_names', None) == []

    @mock.patch('addons.bitbucket.api.BitbucketClient.repos')
    @mock.patch('addons.bitbucket.api.BitbucketClient.team_repos')
    def test_to_json_user_is_not_owner(self, mock_repos, mock_team_repos):
        mock_repos.return_value = []
        mock_team_repos.return_value = []
        not_owner = UserFactory()
        result = self.node_settings.to_json(not_owner)
        assert not result['user_has_auth']
        assert result['bitbucket_user'] == 'abc'
        assert not result['is_owner']
        assert result['valid_credentials']
        assert result.get('repo_names', None) == None


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'bitbucket'
    full_name = 'Bitbucket'
    ExternalAccountFactory = BitbucketAccountFactory

    def test_public_id(self):
        assert self.user.external_accounts.first().display_name == self.user_settings.public_id


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super().setUp()

        self.project = ProjectFactory()
        self.consolidated_auth = Auth(self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )

        self.project.add_addon('bitbucket', auth=self.consolidated_auth)
        self.project.creator.add_addon('bitbucket')
        self.external_account = BitbucketAccountFactory()
        self.project.creator.external_accounts.add(self.external_account)
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
        assert result is None

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
        assert not message

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
        assert message
        assert 'Users can view the contents of this private Bitbucket repository through this public project.' in message[0]

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_repo_deleted(self, mock_repo):
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = None
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert message
        assert 'has been deleted.' in message[0]

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_private_bb_public(self, mock_repo):
        mock_repo.return_value = {'is_private': False}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert message
        assert 'The files in this Bitbucket repo can be viewed on Bitbucket' in message[0]

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    def test_before_page_load_osf_private_bb_private(self, mock_repo):
        mock_repo.return_value = {'is_private': True}
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            user=self.node_settings.user,
            repo=self.node_settings.repo,
        )
        assert not message

    def test_before_page_load_not_contributor(self):
        message = self.node_settings.before_page_load(self.project, UserFactory())
        assert not message

    def test_before_page_load_not_logged_in(self):
        message = self.node_settings.before_page_load(self.project, None)
        assert not message

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert message

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert not message

    def test_after_remove_contributor_authenticator_self(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, self.consolidated_auth
        )
        assert self.node_settings.user_settings is None
        assert message
        assert 'You can re-authenticate' not in message

    def test_after_remove_contributor_authenticator_not_self(self):
        auth = Auth(user=self.non_authenticator)
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, auth
        )
        assert self.node_settings.user_settings is None
        assert message
        assert 'You can re-authenticate' in message

    def test_after_remove_contributor_not_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.non_authenticator, self.consolidated_auth
        )
        assert self.node_settings.user_settings is not None

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert self.node_settings.user_settings == clone.user_settings

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert clone.user_settings is None

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert self.node_settings.user_settings is None

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.project.creator),
            draft_registration=DraftRegistrationFactory(branched_from=self.project),
        )
        assert not registration.has_addon('bitbucket')
