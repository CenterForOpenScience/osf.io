import mock
import unittest
from nose.tools import *

from github3.repos import Repository

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

from framework.auth.decorators import Auth
from website.addons.base import AddonError
from website.addons.github import settings as github_settings


class TestCallbacks(DbTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )
        self.project.save()

        self.project.add_addon('github')
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

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
        # Handle temporary combined files warning; revert later
        assert_equal(len(message), 1)
        #assert_false(message)

    def test_before_page_load_not_logged_in(self):
        message = self.node_settings.before_page_load(self.project, None)
        # Handle temporary combined files warning; revert later
        assert_equal(len(message), 1)

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

    def test_after_remove_contributor_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.project.creator
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )

    def test_after_remove_contributor_not_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_not_equal(
            self.node_settings.user_settings,
            None,
        )

    @unittest.skipIf(not github_settings.SET_PRIVACY, 'Setting privacy is disabled.')
    @mock.patch('website.addons.github.api.GitHub.set_privacy')
    def test_after_set_permissions_private_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_permissions(
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
    def test_after_set_permissions_public_authenticated(self, mock_set_privacy):
        mock_set_privacy.return_value = {}
        message = self.node_settings.after_set_permissions(
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
    def test_after_set_permissions_not_authenticated(self, mock_set_privacy, mock_repo):
        mock_set_privacy.return_value = {'errors': ['it broke']}
        mock_repo.return_value = {'private': True}
        message = self.node_settings.after_set_permissions(
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

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_after_register(self, mock_branches):
        rv = [
            {
                'name': 'master',
                'commit': {
                    'sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc',
                }
            }
        ]
        mock_branches.return_value = rv
        registration = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, registration, self.project.creator,
        )
        mock_branches.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert_equal(
            self.node_settings.user,
            clone.user,
        )
        assert_equal(
            self.node_settings.repo,
            clone.repo,
        )
        assert_equal(
            clone.registration_data,
            {'branches': rv},
        )
        assert_equal(
            clone.user_settings,
            self.node_settings.user_settings
        )

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_after_register_api_fail(self, mock_branches):
        mock_branches.return_value = None
        registration = ProjectFactory()
        with assert_raises(AddonError):
            self.node_settings.after_register(
                self.project, registration, self.project.creator,
            )
        mock_branches.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
