"""
Tests related to authenticating API requests
"""

import mock

from nose.tools import *  # flake8: noqa

from framework.auth import cas
from website.util import api_v2_url
from website.addons.twofactor.tests import _valid_code

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, ProjectFactory, UserFactory

from api.base.settings import API_BASE


class TestBasicAuthenticationValidation(ApiTestCase):
    """Test that APIv2 requests can validate and respond to Basic Authentication"""

    TOTP_SECRET = 'b8f85986068f8079aa9d'

    def setUp(self):
        super(TestBasicAuthenticationValidation, self).setUp()
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        # Test projects for which a given user DOES and DOES NOT  have appropriate permissions
        self.reachable_project = ProjectFactory(title="Private Project User 1", is_public=False, creator=self.user1)
        self.unreachable_project = ProjectFactory(title="Private Project User 2", is_public=False, creator=self.user2)
        self.reachable_url = "/{}nodes/{}/".format(API_BASE, self.reachable_project._id)
        self.unreachable_url = "/{}nodes/{}/".format(API_BASE, self.unreachable_project._id)  # User1 can't access this

    def test_missing_credential_fails(self):
        res = self.app.get(self.unreachable_url, auth=None, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json.get("errors")[0]['detail'], 'Authentication credentials were not provided.')

    def test_invalid_credential_fails(self):
        res = self.app.get(self.unreachable_url, auth=(self.user1.username, 'invalid password'), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json.get("errors")[0]['detail'], 'Invalid username/password.')

    def test_valid_credential_authenticates_and_has_permissions(self):
        res = self.app.get(self.reachable_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200, msg=res.json)

    def test_valid_credential_authenticates_but_user_lacks_object_permissions(self):
        res = self.app.get(self.unreachable_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 403, msg=res.json)

    def test_valid_credential_but_twofactor_required(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.headers['X-OSF-OTP'], 'required; app')
        assert_equal(res.json.get("errors")[0]['detail'], 'Must specify two-factor authentication OTP code.')

    def test_valid_credential_twofactor_invalid_otp(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, headers={'X-OSF-OTP': 'invalid otp'}, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_true('X-OSF-OTP' not in res.headers)
        assert_equal(res.json.get("errors")[0]['detail'], 'Invalid two-factor authentication OTP code.')

    def test_valid_credential_twofactor_valid_otp(self):
        user1_addon = self.user1.get_or_add_addon('twofactor')
        user1_addon.totp_drift = 1
        user1_addon.totp_secret = self.TOTP_SECRET
        user1_addon.is_confirmed = True
        user1_addon.save()

        res = self.app.get(self.reachable_url, auth=self.user1.auth, headers={'X-OSF-OTP': _valid_code(self.TOTP_SECRET)})
        assert_equal(res.status_code, 200)


class TestOAuthValidation(ApiTestCase):
    """Test that APIv2 requests can validate and respond to OAuth2 bearer tokens"""
    def setUp(self):
        super(TestOAuthValidation, self).setUp()
        self.user1 = UserFactory()
        self.user2 = UserFactory()

        # Test projects for which a given user DOES and DOES NOT  have appropriate permissions
        self.reachable_project = ProjectFactory(title="Private Project User 1", is_public=False, creator=self.user1)
        self.unreachable_project = ProjectFactory(title="Private Project User 2", is_public=False, creator=self.user2)

        self.reachable_url = "/{}nodes/{}/".format(API_BASE, self.reachable_project._id)
        self.unreachable_url = "/{}nodes/{}/".format(API_BASE, self.unreachable_project._id)  # User1 can't access this

    def test_missing_token_fails(self):
        res = self.app.get(self.reachable_url, auth=None, auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json.get("errors")[0]['detail'],
                     'Authentication credentials were not provided.')

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_invalid_token_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=False, user=None,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = self.app.get(self.reachable_url, auth='invalid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 401, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_returns_unknown_user_thus_fails(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user='fail',
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = self.app.get(self.reachable_url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 401, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_and_has_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = self.app.get(self.reachable_url, auth='some_valid_token', auth_type='jwt')
        assert_equal(res.status_code, 200, msg=res.json)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_but_user_lacks_object_permissions(self, mock_user_info):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=self.user1._id,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = self.app.get(self.unreachable_url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403, msg=res.json)


class TestOAuthScopedAccess(ApiTestCase):
    """Verify that OAuth2 scopes restrict APIv2 access for a few sample views. These tests cover basic mechanics,
        but are not intended to be an exhaustive list of how all views respond to all scopes."""
    def setUp(self):
        super(TestOAuthScopedAccess, self).setUp()
        self.user = UserFactory()
        self.user2 = UserFactory()  # Todo move inside tests that need this
        self.project = ProjectFactory(creator=self.user)

    def _scoped_response(self, scopes_list, user=None):
        user = user or self.user
        return cas.CasResponse(authenticated=True, user=user._id, attributes={'accessTokenScope': scopes_list})

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_can_read_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = self.app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_cant_write_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {'data': {'type': 'users', 'id': self.user._id, 'attributes': {u'suffix': u'VIII'}}}

        res = self.app.patch_json_api(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_implies_read_permissions_for_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = self.app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_can_write_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.users.all_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {'data': {'type': 'users', 'id': self.user._id, 'attributes': {u'suffix': u'VIII'}}}

        res = self.app.patch_json_api(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_dict_contains_subset(payload['data']['attributes'],
                                    res.json['data']['attributes'])

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_node_write_scope_cant_read_user_view(self, mock_user_info):
        mock_user_info.return_value = self._scoped_response(['osf.nodes.all_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {u'suffix': u'VIII'}

        res = self.app.get(url, params=payload, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert_equal(res.status_code, 403)
