# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
import datetime
import unittest
import pytest

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, UserFactory, AuthUserFactory

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.util import api_url_for
from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.bitbucket import utils
from addons.bitbucket.api import BitbucketClient
from addons.bitbucket.models import BitbucketProvider
from addons.bitbucket.serializer import BitbucketSerializer
from addons.bitbucket.tests.factories import BitbucketAccountFactory
from addons.bitbucket.tests.utils import BitbucketAddonTestCase, create_mock_bitbucket

pytestmark = pytest.mark.django_db


class TestBitbucketAuthViews(BitbucketAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    @mock.patch(
        'addons.bitbucket.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestBitbucketAuthViews, self).test_delete_external_account()


class TestBitbucketConfigViews(BitbucketAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = None
    Serializer = BitbucketSerializer
    client = BitbucketClient

    ## Overrides ##

    def setUp(self):
        super(TestBitbucketConfigViews, self).setUp()
        self.mock_access_token = mock.patch('addons.bitbucket.models.BitbucketProvider.fetch_access_token')
        self.mock_access_token.return_value = mock.Mock()
        self.mock_access_token.start()

    def tearDown(self):
        self.mock_access_token.stop()
        super(TestBitbucketConfigViews, self).tearDown()

    def test_folder_list(self):
        # BB only lists root folder (repos), this test is superfluous
        pass

    @mock.patch('addons.bitbucket.views.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_set_config(self, mock_account, mock_repo):
        # BB selects repos, not folders, so this needs to be overriden
        mock_account.return_value = mock.Mock()
        mock_repo.return_value = 'repo_name'
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.post_json(url, {
            'bitbucket_user': 'octocat',
            'bitbucket_repo': 'repo_name',
        }, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.project.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_repo_linked'.format(self.ADDON_SHORT_NAME)
        )


class TestBitbucketViews(OsfTestCase):

    def setUp(self):
        super(TestBitbucketViews, self).setUp()
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)

        self.project = ProjectFactory(creator=self.user)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.save()

        self.external_account = BitbucketAccountFactory()

        self.project.add_addon('bitbucket', auth=self.consolidated_auth)
        self.project.creator.add_addon('bitbucket')
        self.project.creator.external_accounts.add(self.external_account)
        self.project.creator.save()

        self.bitbucket = create_mock_bitbucket(user='fred', private=False)

        self.user_settings = self.project.creator.get_addon('bitbucket')
        self.user_settings.oauth_grants[self.project._id] = {self.external_account._id: []}
        self.user_settings.save()

        self.node_settings = self.project.get_addon('bitbucket')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.external_account = self.external_account
        self.node_settings.user = self.bitbucket.repo.return_value['owner']['username']
        self.node_settings.repo = self.bitbucket.repo.return_value['name']
        self.node_settings.save()

    def _get_sha_for_branch(self, branch=None, mock_branches=None):
        bitbucket_mock = self.bitbucket
        if mock_branches is None:
            mock_branches = bitbucket_mock.branches
        if branch is None:  # Get default branch name
            branch = self.bitbucket.repo_default_branch.return_value
        for each in mock_branches.return_value:
            if each['name'] == branch:
                branch_sha = each['target']['hash']
        return branch_sha

    # Tests for _get_refs
    @mock.patch('addons.bitbucket.api.BitbucketClient.branches')
    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.api.BitbucketClient.repo_default_branch')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_get_refs_defaults(self, mock_account, mock_default_branch, mock_repo, mock_branches):
        bitbucket_mock = self.bitbucket
        mock_account.return_value = mock.Mock()
        mock_default_branch.return_value = bitbucket_mock.repo_default_branch.return_value
        mock_repo.return_value = bitbucket_mock.repo.return_value
        mock_branches.return_value = bitbucket_mock.branches.return_value

        branch, sha, branches = utils.get_refs(self.node_settings)
        assert_equal(
            branch,
            bitbucket_mock.repo_default_branch.return_value
        )
        assert_equal(sha, self._get_sha_for_branch(branch=None))  # Get refs for default branch

        expected_branches = [
            {'name': x['name'], 'sha': x['target']['hash']}
            for x in bitbucket_mock.branches.return_value
        ]
        assert_equal(branches, expected_branches)

    @mock.patch('addons.bitbucket.api.BitbucketClient.branches')
    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.api.BitbucketClient.repo_default_branch')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_get_refs_branch(self, mock_account, mock_default_branch, mock_repo, mock_branches):
        bitbucket_mock = self.bitbucket
        mock_account.return_value = mock.Mock()
        mock_default_branch.return_value = bitbucket_mock.repo_default_branch.return_value
        mock_repo.return_value = bitbucket_mock.repo.return_value
        mock_branches.return_value = bitbucket_mock.branches.return_value

        branch, sha, branches = utils.get_refs(self.node_settings, 'master')
        assert_equal(branch, 'master')
        branch_sha = self._get_sha_for_branch('master')
        assert_equal(sha, branch_sha)

        expected_branches = [
            {'name': x['name'], 'sha': x['target']['hash']}
            for x in bitbucket_mock.branches.return_value
        ]
        assert_equal(branches, expected_branches)

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(len(res.json['prompts']), 1)

    def test_before_register(self):
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_true('Bitbucket' in res.json['prompts'][1])

    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_get_refs_sha_no_branch(self, mock_account):
        with assert_raises(HTTPError):
            utils.get_refs(self.node_settings, sha='12345')

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='bitbucket')
        expected_urls = {
            'view': '{0}?ref={1}'.format(url, sha),
            'download': '{0}?action=download&ref={1}'.format(url, sha)
        }

        assert_equal(urls['view'], expected_urls['view'])
        assert_equal(urls['download'], expected_urls['download'])


class TestBitbucketSettings(OsfTestCase):

    def setUp(self):

        super(TestBitbucketSettings, self).setUp()
        self.bitbucket = create_mock_bitbucket(user='fred', private=False)
        self.project = ProjectFactory()
        self.project.save()
        self.auth = self.project.creator.auth
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('bitbucket', auth=self.consolidated_auth)
        self.project.creator.add_addon('bitbucket')
        self.node_settings = self.project.get_addon('bitbucket')
        self.user_settings = self.project.creator.get_addon('bitbucket')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_link_repo(self, mock_account, mock_repo):
        bitbucket_mock = self.bitbucket
        mock_account.return_value = mock.Mock()
        mock_repo.return_value = bitbucket_mock.repo.return_value

        url = self.project.api_url + 'bitbucket/settings/'
        self.app.post_json(
            url,
            {
                'bitbucket_user': 'queen',
                'bitbucket_repo': 'night at the opera',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.user, 'queen')
        assert_equal(self.node_settings.repo, 'night at the opera')
        assert_equal(self.project.logs.latest().action, 'bitbucket_repo_linked')

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_link_repo_no_change(self, mock_account, mock_repo):
        bitbucket_mock = self.bitbucket
        mock_account.return_value = mock.Mock()
        mock_repo.return_value = bitbucket_mock.repo.return_value

        log_count = self.project.logs.count()

        url = self.project.api_url + 'bitbucket/settings/'
        self.app.post_json(
            url,
            {
                'bitbucket_user': 'Queen',
                'bitbucket_repo': 'Sheer-Heart-Attack',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.project.logs.count(), log_count)

    @mock.patch('addons.bitbucket.api.BitbucketClient.repo')
    @mock.patch('addons.bitbucket.models.NodeSettings.external_account')
    def test_link_repo_non_existent(self, mock_account, mock_repo):
        mock_account.return_value = mock.Mock()
        mock_repo.return_value = None

        url = self.project.api_url + 'bitbucket/settings/'
        res = self.app.post_json(
            url,
            {
                'bitbucket_user': 'queen',
                'bitbucket_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    @mock.patch('addons.bitbucket.api.BitbucketClient.branches')
    def test_link_repo_registration(self, mock_branches):
        bitbucket_mock = self.bitbucket
        mock_branches.return_value = bitbucket_mock.branches.return_value

        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=self.consolidated_auth,
            data=''
        )

        url = registration.api_url + 'bitbucket/settings/'
        res = self.app.post_json(
            url,
            {
                'bitbucket_user': 'queen',
                'bitbucket_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    def test_deauthorize(self):

        url = self.project.api_url + 'bitbucket/user_auth/'

        self.app.delete(url, auth=self.auth).maybe_follow()

        self.project.reload()
        self.node_settings.reload()
        assert_equal(self.node_settings.user, None)
        assert_equal(self.node_settings.repo, None)
        assert_equal(self.node_settings.user_settings, None)

        assert_equal(self.project.logs.latest().action, 'bitbucket_node_deauthorized')


if __name__ == '__main__':
    unittest.main()
