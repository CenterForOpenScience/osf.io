import copy
import mock

from nose.tools import *  # flake8: noqa

from website.models import User, ApiOAuth2PersonalToken
from website.util import api_v2_url

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2PersonalTokenFactory, AuthUserFactory

TOKEN_LIST_URL = api_v2_url('tokens/', base_route='/')

def _get_token_detail_route(token):
    path = "tokens/{}/".format(token._id)
    return api_v2_url(path, base_route='/')


class TestTokenDetail(ApiTestCase):
    def setUp(self):
        super(TestTokenDetail, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_token = ApiOAuth2PersonalTokenFactory(owner=self.user1, user_id=self.user1._id)
        self.user1_token_url = _get_token_detail_route(self.user1_token)

        self.missing_type = {
            'data': {
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': 'osf.full_write',
                }
            }
        }

        self.incorrect_type = {
            'data': {
                'type': 'Wrong type.',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': 'osf.full_write',
                }
            }
        }

        self.injected_scope = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny invalid token',
                    'scopes': 'osf.admin',
                }
            }
        }

        self.nonsense_scope = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny invalid token',
                    'scopes': 'osf.nonsense',
                }
            }
        }

        self.correct = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': 'osf.full_write',
                }
            }
        }

    def test_owner_can_view(self):
        res = self.app.get(self.user1_token_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user1_token._id)

    def test_non_owner_cant_view(self):
        res = self.app.get(self.user1_token_url, auth=self.user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_401_when_not_logged_in(self):
        res = self.app.get(self.user1_token_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_owner_can_delete(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        assert_equal(res.status_code, 204)

    def test_non_owner_cant_delete(self):
        res = self.app.delete(self.user1_token_url,
                              auth=self.user2.auth,
                              expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_tokens_makes_api_view_inaccessible(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        res = self.app.get(self.user1_token_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_updating_one_field_should_not_blank_others_on_patch_update(self, mock_revoke):
        mock_revoke.return_value = True
        user1_token = self.user1_token
        new_name = "The token formerly known as Prince"
        res = self.app.patch_json_api(self.user1_token_url,
                             {'data': {'attributes':
                                  {'name': new_name, 'scopes':'osf.full_write'},
                              'id': self.user1_token._id,
                              'type': 'tokens'
                             }}, auth=self.user1.auth)
        user1_token.reload()
        assert_equal(res.status_code, 200)

        assert_dict_contains_subset({'owner': user1_token.owner._id,
                                     'name': new_name,
                                     'scopes': '{}'.format(user1_token.scopes),
                                     },
                                    res.json['data']['attributes'])
        assert_equal(res.json['data']['id'], user1_token._id)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_updating_an_instance_does_not_change_the_number_of_instances(self, mock_revoke):
        mock_revoke.return_value = True
        new_name = "The token formerly known as Prince"
        res = self.app.patch_json_api(self.user1_token_url,
                                      {'data': {
                                          'attributes': {"name": new_name, 'scopes':'osf.full_write'},
                                          'id': self.user1_token._id,
                                          'type': 'tokens'}}, auth=self.user1.auth)
        assert_equal(res.status_code, 200)

        list_url = TOKEN_LIST_URL
        res = self.app.get(list_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     1)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_flags_instance_inactive(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        self.user1_token.reload()
        assert_false(self.user1_token.is_active)

    def test_read_does_not_return_token_id(self):
        res = self.app.get(self.user1_token_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_false(res.json['data']['attributes'].has_key('token_id'))

    def test_create_with_admin_scope_fails(self):
        res = self.app.post_json_api(TOKEN_LIST_URL, self.injected_scope, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        
    def test_create_with_fake_scope_fails(self):
        res = self.app.post_json_api(TOKEN_LIST_URL, self.nonsense_scope, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_with_admin_scope_fails(self):
        res = self.app.put_json_api(self.user1_token_url, self.injected_scope, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_with_fake_scope_fails(self):
        res = self.app.put_json_api(self.user1_token_url, self.nonsense_scope, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token_does_not_return_token_id(self, mock_revoke):
        mock_revoke.return_value = True
        res = self.app.put_json_api(self.user1_token_url, self.correct, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_false(res.json['data']['attributes'].has_key('token_id'))

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_update_token(self, mock_revoke):
        mock_revoke.return_value = True
        res = self.app.put_json_api(self.user1_token_url, self.correct, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_update_token_incorrect_type(self):
        res = self.app.put_json_api(self.user1_token_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_token_no_type(self):
        res = self.app.put_json_api(self.user1_token_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_token_no_attributes(self):
        payload = {'id': self.user1_token._id, 'type': 'tokens', 'name': 'The token formerly known as Prince'}
        res = self.app.put_json_api(self.user1_token_url, payload, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_token_incorrect_type(self):
        res = self.app.patch_json_api(self.user1_token_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_token_no_type(self):
        res = self.app.patch_json_api(self.user1_token_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_token_no_attributes(self):
        payload = {
            'data':
                {'id': self.user1_token._id,
                 'type': 'tokens',
                 'name': 'The token formerly known as Prince'
                 }
        }
        res = self.app.patch_json_api(self.user1_token_url, payload, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def tearDown(self):
        super(TestTokenDetail, self).tearDown()
        ApiOAuth2PersonalToken.remove()
        User.remove()
