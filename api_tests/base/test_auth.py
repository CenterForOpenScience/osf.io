"""
Tests related to authenticating API requests
"""

import mock
import pytest

from addons.twofactor.tests import _valid_code
from api.base.settings import API_BASE
from framework.auth import cas, core, oauth_scopes
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
)
from tests.base import assert_dict_contains_subset
from website.util import api_v2_url
from website.settings import API_DOMAIN


@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()

@pytest.mark.django_db
class TestBasicAuthenticationValidation:
    """Test that APIv2 requests can validate and respond to Basic Authentication"""

    TOTP_SECRET = 'b8f85986068f8079aa9d'

    # Test projects for which a given user DOES and DOES NOT  have appropriate permissions
    @pytest.fixture()
    def project_reachable(self, user_one):
        return ProjectFactory(title="Private Project User 1", is_public=False, creator=user_one)

    @pytest.fixture()
    def project_unreachable(self, user_two):
        return ProjectFactory(title="Private Project User 2", is_public=False, creator=user_two)

    @pytest.fixture()
    def url_reachable(self, project_reachable):
        return "/{}nodes/{}/".format(API_BASE, project_reachable._id)

    @pytest.fixture()
    def url_unreachable(self, project_unreachable):
        return "/{}nodes/{}/".format(API_BASE, project_unreachable._id)  # User_one can't access this

    def test_missing_credential_fails(self, app, url_unreachable):
        res = app.get(url_unreachable, auth=None, expect_errors=True)
        assert res.status_code == 401
        assert res.json.get("errors")[0]['detail'] == 'Authentication credentials were not provided.'

    def test_invalid_credential_fails(self, app, url_unreachable, user_one):
        res = app.get(url_unreachable, auth=(user_one.username, 'invalid password'), expect_errors=True)
        assert res.status_code == 401
        assert res.json.get("errors")[0]['detail'] == 'Invalid username/password.'

    def test_valid_credential_authenticates_and_has_permissions(self, app, url_reachable, user_one):
        res = app.get(url_reachable, auth=user_one.auth)
        assert res.status_code == 200, res.json

    def test_valid_credential_authenticates_but_user_lacks_object_permissions(self, app, url_unreachable, user_one):
        res = app.get(url_unreachable, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 403, res.json

    def test_valid_credential_but_twofactor_required(self, app, user_one, url_reachable):
        user_one_addon = user_one.get_or_add_addon('twofactor')
        user_one_addon.totp_drift = 1
        user_one_addon.totp_secret = self.TOTP_SECRET
        user_one_addon.is_confirmed = True
        user_one_addon.save()

        res = app.get(url_reachable, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 401
        assert res.headers['X-OSF-OTP'] == 'required; app'
        assert res.json.get("errors")[0]['detail'] == 'Must specify two-factor authentication OTP code.'

    def test_valid_credential_twofactor_invalid_otp(self, app, user_one, url_reachable):
        user_one_addon = user_one.get_or_add_addon('twofactor')
        user_one_addon.totp_drift = 1
        user_one_addon.totp_secret = self.TOTP_SECRET
        user_one_addon.is_confirmed = True
        user_one_addon.save()

        res = app.get(url_reachable, auth=user_one.auth, headers={'X-OSF-OTP': 'invalid otp'}, expect_errors=True)
        assert res.status_code == 401
        assert 'X-OSF-OTP' not in res.headers
        assert res.json.get("errors")[0]['detail'] == 'Invalid two-factor authentication OTP code.'

    def test_valid_credential_twofactor_valid_otp(self, app, user_one, url_reachable, ):
        user_one_addon = user_one.get_or_add_addon('twofactor')
        user_one_addon.totp_drift = 1
        user_one_addon.totp_secret = self.TOTP_SECRET
        user_one_addon.is_confirmed = True
        user_one_addon.save()

        res = app.get(url_reachable, auth=user_one.auth, headers={'X-OSF-OTP': _valid_code(self.TOTP_SECRET)})
        assert res.status_code == 200


@pytest.mark.django_db
class TestOAuthValidation:
    """Test that APIv2 requests can validate and respond to OAuth2 bearer tokens"""

    @pytest.fixture()
    def project_reachable(self, user_one):
        return ProjectFactory(title="Private Project User 1", is_public=False, creator=user_one)

    @pytest.fixture()
    def project_unreachable(self, user_two):
        return ProjectFactory(title="Private Project User 2", is_public=False, creator=user_two)

    @pytest.fixture()
    def url_reachable(self, project_reachable):
        return "/{}nodes/{}/".format(API_BASE, project_reachable._id)

    @pytest.fixture()
    def url_unreachable(self, project_unreachable):
        return "/{}nodes/{}/".format(API_BASE, project_unreachable._id)  # User_one can't access this

    def test_missing_token_fails(self, app, url_reachable):
        res = app.get(url_reachable, auth=None, auth_type='jwt', expect_errors=True)
        assert res.status_code == 401
        assert (res.json.get("errors")[0]['detail'] ==
                     'Authentication credentials were not provided.')

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_invalid_token_fails(self, mock_user_info, app, url_reachable):
        mock_user_info.return_value = cas.CasResponse(authenticated=False, user=None,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = app.get(url_reachable, auth='invalid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 401, res.json

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_returns_unknown_user_thus_fails(self, mock_user_info, app, url_reachable):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user='fail',
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = app.get(url_reachable, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 401, res.json

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_and_has_permissions(self, mock_user_info, app, user_one, url_reachable):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=user_one._id,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = app.get(url_reachable, auth='some_valid_token', auth_type='jwt')
        assert res.status_code == 200, res.json

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_valid_token_authenticates_but_user_lacks_object_permissions(self, mock_user_info, app, url_unreachable, user_one):
        mock_user_info.return_value = cas.CasResponse(authenticated=True, user=user_one._id,
                                                      attributes={'accessTokenScope': ['osf.full_read']})

        res = app.get(url_unreachable, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 403, res.json

@pytest.mark.django_db
class TestOAuthScopedAccess:
    """Verify that OAuth2 scopes restrict APIv2 access for a few sample views. These tests cover basic mechanics,
        but are not intended to be an exhaustive list of how all views respond to all scopes."""

    @pytest.fixture()
    def user_one(self):
        return UserFactory()

    @pytest.fixture()
    def user_two(self):
        return UserFactory()  # Todo move inside tests that need this

    @pytest.fixture()
    def project(self, user_one):
        return ProjectFactory(creator=user_one)

    @pytest.fixture()
    def _scoped_response(self, user_one):
        def _response(scopes_list):
            return cas.CasResponse(authenticated=True, user=user_one._id, attributes={'accessTokenScope': scopes_list})
        return _response

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_can_read_user_view(self, mock_user_info, app, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 200

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_read_scope_cant_write_user_view(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {'data': {'type': 'users', 'id': user_one._id, 'attributes': {u'suffix': u'VIII'}}}

        res = app.patch_json_api(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 403

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_implies_read_permissions_for_user_view(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 200

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_write_scope_can_write_user_view(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {'data': {'type': 'users', 'id': user_one._id, 'attributes': {u'suffix': u'VIII'}}}

        res = app.patch_json_api(url, params=payload,
                             auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 200
        res_attributes = res.json['data']['attributes']
        res_attributes.pop('social', None)
        assert_dict_contains_subset(payload['data']['attributes'], res_attributes)

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_node_write_scope_cant_read_user_view(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.nodes.full_write'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        payload = {u'suffix': u'VIII'}

        res = app.get(url, params=payload, auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert res.status_code == 403

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_full_read_scope_can_read_guid_view_and_user_can_view_project(self, mock_user_info, app, project, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.full_read'])
        url = api_v2_url('guids/{}/'.format(project._id), base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert res.status_code == 302
        assert res.location == redirect_url
        redirect_res = res.follow(auth='some_valid_token', auth_type='jwt')
        assert redirect_res.json['data']['attributes']['title'] == project.title

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_full_write_scope_can_read_guid_view_and_user_can_view_project(self, mock_user_info, app, project, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.full_write'])
        url = api_v2_url('guids/{}/'.format(project._id), base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert res.status_code == 302
        assert res.location == redirect_url
        redirect_res = res.follow(auth='some_valid_token', auth_type='jwt')
        assert redirect_res.json['data']['attributes']['title'] == project.title

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_full_read_scope_can_read_guid_view_and_user_cannot_view_project(self, mock_user_info, app, user_one, _scoped_response):
        project = ProjectFactory()
        mock_user_info.return_value = _scoped_response(['osf.full_read'])
        url = api_v2_url('guids/{}/'.format(project._id), base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert res.status_code == 302
        assert res.location == redirect_url
        redirect_res = res.follow(auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert redirect_res.status_code == 403

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_full_write_scope_can_read_guid_view_and_user_cannot_view_project(self, mock_user_info, app, user_one, _scoped_response):
        project = ProjectFactory()
        mock_user_info.return_value = _scoped_response(['osf.full_write'])
        url = api_v2_url('guids/{}/'.format(project._id), base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        redirect_url = '{}{}nodes/{}/'.format(API_DOMAIN, API_BASE, project._id)
        assert res.status_code == 302
        assert res.location == redirect_url
        redirect_res = res.follow(auth='some_valid_token', auth_type='jwt', expect_errors=True)
        assert redirect_res.status_code == 403

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_email_scope_can_read_email(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_read', 'osf.users.email_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        assert res.status_code == 200
        assert res.json['data']['attributes']['email'] == user_one.username

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_non_user_email_scope_cannot_read_email(self, mock_user_info, app, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_read'])
        url = api_v2_url('users/me/', base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        assert res.status_code == 200
        assert 'email' not in res.json['data']['attributes']
        assert user_one.username not in res.json

    @mock.patch('framework.auth.cas.CasClient.profile')
    def test_user_email_scope_cannot_read_other_email(self, mock_user_info, app, user_two, user_one, _scoped_response):
        mock_user_info.return_value = _scoped_response(['osf.users.profile_read', 'osf.users.email_read'])
        url = api_v2_url('users/{}/'.format(user_two._id), base_route='/', base_prefix='v2/')
        res = app.get(url, auth='some_valid_token', auth_type='jwt')
        assert res.status_code == 200
        assert 'email' not in res.json['data']['attributes']
        assert user_two.username not in res.json
