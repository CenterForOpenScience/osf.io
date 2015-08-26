"""
Tests related to authenticating API requests
"""

import mock

from nose.tools import *  # flake8: noqa

from framework.auth import cas
from website.util import api_v2_url

from tests.base import ApiTestCase
from tests.factories import ProjectFactory, UserFactory

from api.base.settings import API_BASE


class TestOAuthValidation(ApiTestCase):
    """Test that OAuth2 requests can be validated"""
    def setUp(self):
        super(TestOAuthValidation, self).setUp()
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        # Test projects for which a given user DOES and DOES NOT  have appropriate permissions
        self.reachable_project = ProjectFactory(title="Private Project User 1", is_public=False, creator=self.user1)
        self.unreachable_project = ProjectFactory(title="Private Project User 2", is_public=False, creator=self.user2)

        self.reachable_url = "/{}nodes/{}/".format(API_BASE, self.reachable_project._id)
        self.unreachable_url = "/{}nodes/{}/".format(API_BASE, self.unreachable_project._id)

    def test_missing_token_fails(self):
        res = self.app.get(self.reachable_url, auth=None, auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json.get("detail"),
                     'Authentication credentials were not provided.')

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_invalid_token_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=False, user=None)

        res = self.app.get(self.reachable_url, auth='invalid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_returns_unknown_user_thus_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user='fail')

        res = self.app.get(self.reachable_url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_and_has_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id)

        res = self.app.get(self.reachable_url, auth='some_valid_token', auth_type='jwt')
        assert_equal(res.status_code, 200, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_but_user_lacks_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id)

        res = self.app.get(self.unreachable_url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403, msg=res.json)

# TODO: Add unit tests to deal with scopes. Validate sample access to a few views.
class TestOAuthScopedAccess(ApiTestCase):
    """Verify that scopes restrict access for a few sample views. These tests cover basic mechanics,
        but are not intended to be an exhaustive list of how all views respond to all scopes."""
    def setUp(self):
        super(TestOAuthScopedAccess, self).setUp()
        self.user = UserFactory()
        self.user2 = UserFactory()  # Todo move inside tests that need this
        self.project = ProjectFactory(creator=self.user)

    def _scoped_response(self, scopes_list, user=None):
        user = user or self.user
        return cas.CasResponse(authenticated=True, user=user._id, scope=scopes_list)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_can_read_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all+read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = self.app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_cant_write_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all+read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {u'suffix': u'VIII'}

        res = self.app.patch(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_implies_read_permissions_for_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all+write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = self.app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_can_write_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all+write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {u'suffix': u'VIII'}

        res = self.app.patch(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_dict_contains_subset(payload,
                                    res.json['data'])
