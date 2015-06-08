"""
Tests related to authenticating API requests
"""

import mock

from nose.tools import *  # flake8: noqa

from framework.auth import cas
from tests.base import ApiTestCase
from tests.factories import ProjectFactory, UserFactory


class TestOAuthValidation(ApiTestCase):
    """Test that OAuth2 requests can be validated"""
    def setUp(self):
        super(TestOAuthValidation, self).setUp()
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        # Test projects for which a given user DOES and DOES NOT  have appropriate permissions
        self.reachable_project = ProjectFactory(title="Private Project User 1", is_public=False, creator=self.user1)
        self.unreachable_project = ProjectFactory(title="Private Project User 2", is_public=False, creator=self.user2)

        self.reachable_url = "/v2/nodes/{}/".format(self.reachable_project._id)
        self.unreachable_url = "/v2/nodes/{}/".format(self.unreachable_project._id)

    def _make_request(self, url, access_token=None):
        """Helper function to make a request with auth headers"""
        if access_token:
            headers = {'Authorization': 'Bearer {}'.format(access_token)}
        else:
            headers = None

        res = self.app.get(url, expect_errors=True, headers=headers)
        return res

    def test_missing_token_fails(self):
        url = "/v2/nodes/{}/".format(self.reachable_project._id)
        res = self._make_request(url, access_token=None)

        assert_equal(res.status_code, 403)
        assert_equal(res.json.get("detail"),
                     'Authentication credentials were not provided.')

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_invalid_token_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=False, user=None)

        res = self._make_request(self.reachable_url, access_token="invalid_token")

        assert_equal(res.status_code, 403, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_returns_unknown_user_thus_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user='fail')

        res = self._make_request(self.reachable_url, access_token="some_valid_token")

        assert_equal(res.status_code, 403, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_and_has_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id)

        res = self._make_request(self.reachable_url, access_token="some_valid_token")

        assert_equal(res.status_code, 200, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_but_user_lacks_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id)

        res = self._make_request(self.unreachable_url, access_token="some_valid_token")
        assert_equal(res.status_code, 403, msg=res.json)
