import copy
import mock

from nose.tools import *  # flake8: noqa

from api.tokens.models import ApiOAuth2PersonalToken
from website.models import User
from website.util import api_v2_url
from website.util import sanitize

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2PersonalTokenFactory, AuthUserFactory


def _get_token_detail_route(token):
    path = "tokens/{}/".format(token._id)
    return api_v2_url(path, base_route='/')


def _get_token_list_url():
    path = "tokens/"
    return api_v2_url(path, base_route='/')


class TestTokenList(ApiTestCase):
    def setUp(self):
        super(TestTokenList, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_tokens = [ApiOAuth2PersonalTokenFactory(owner=self.user1) for i in xrange(3)]
        self.user2_tokens = [ApiOAuth2PersonalTokenFactory(owner=self.user2) for i in xrange(2)]

        self.user1_list_url = _get_token_list_url()
        self.user2_list_url = _get_token_list_url()

        self.sample_data = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny new token',
                    'scopes': ['osf.full_write'],
                    'owner': 'Value discarded',
                    'token_id': 'Value discarded',
                }
            }
        }

    def test_user1_should_see_only_their_tokens(self):
        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(len(res.json['data']),
                     len(self.user1_tokens))

    def test_user2_should_see_only_their_tokens(self):
        res = self.app.get(self.user2_list_url, auth=self.user2.auth)
        assert_equal(len(res.json['data']),
                     len(self.user2_tokens))

    # @mock.patch('framework.auth.cas.CasClient.revoke_personal_tokens')
    # def test_deleting_token_should_hide_it_from_api_list(self, mock_method):
        # mock_method.return_value(True)
        # api_token = self.user1_tokens[0]
        # url = _get_token_detail_route(api_token)
# 
        # res = self.app.delete(url, auth=self.user1.auth)
        # assert_equal(res.status_code, 204)
# 
        # res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        # assert_equal(res.status_code, 200)
        # assert_equal(len(res.json['data']),
                     # len(self.user1_tokens) - 1)

    def test_created_tokens_are_tied_to_request_user_with_data_specified(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 201)

        assert_equal(res.json['data']['attributes']['owner'], self.user1._id)
        # Some fields aren't writable; make sure user can't set these
        import ipdb; ipdb.set_trace()
        assert_not_equal(res.json['data']['attributes']['token_id'],
                         self.sample_data['data']['attributes']['token_id'])

    def test_field_content_is_sanitized_upon_submission(self):
        bad_text = "<a href='http://sanitized.name'>User_text</a>"
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.copy(self.sample_data)
        payload['data']['attributes']['name'] = bad_text

        res = self.app.post_json_api(self.user1_list_url, payload, auth=self.user1.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], cleaned_text)

    def test_created_tokens_show_up_in_api_list(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth)
        assert_equal(res.status_code, 201)

        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(len(res.json['data']),
                     len(self.user1_tokens) + 1)

    def test_returns_401_when_not_logged_in(self):
        res = self.app.get(self.user1_list_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def tearDown(self):
        super(TestTokenList, self).tearDown()
        ApiOAuth2PersonalToken.remove()
        User.remove()


class TestTokenDetail(ApiTestCase):
    def setUp(self):
        super(TestTokenDetail, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_token = ApiOAuth2PersonalTokenFactory(owner=self.user1)
        self.user1_token_url = _get_token_detail_route(self.user1_token)

        self.missing_id = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': ['osf.full_write'],
                }
            }
        }

        self.missing_type = {
            'data': {
                'id': self.user1_token._id,
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': ['osf.full_write'],
                }
            }
        }

        self.incorrect_id = {
            'data': {
                'id': '12345',
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': ['osf.full_write'],
                }
            }
        }

        self.incorrect_type = {
            'data': {
                'id': self.user1_token._id,
                'type': 'Wrong type.',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': ['osf.full_write'],
                }
            }
        }

        self.correct = {
            'data': {
                'id': self.user1_token._id,
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny updated token',
                    'scopes': ['osf.full_write'],
                }
            }
        }

    def test_owner_can_view(self):
        res = self.app.get(self.user1_token_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['_id'], self.user1_token._id)

    def test_non_owner_cant_view(self):
        res = self.app.get(self.user1_token_url, auth=self.user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_401_when_not_logged_in(self):
        res = self.app.get(self.user1_token_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    # @mock.patch('framework.auth.cas.CasClient.revoke_personal_tokens')
    # def test_owner_can_delete(self, mock_method):
        # mock_method.return_value(True)
        # res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        # assert_equal(res.status_code, 204)

    def test_non_owner_cant_delete(self):
        res = self.app.delete(self.user1_token_url,
                              auth=self.user2.auth,
                              expect_errors=True)
        assert_equal(res.status_code, 403)

    # @mock.patch('framework.auth.cas.CasClient.revoke_personal_tokens')
    # def test_deleting_tokens_makes_api_view_inaccessible(self, mock_method):
        # mock_method.return_value(True)
        # res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        # res = self.app.get(self.user1_token_url, auth=self.user1.auth, expect_errors=True)
        # assert_equal(res.status_code, 404)

    def test_updating_one_field_should_not_blank_others_on_patch_update(self):
        user1_token = self.user1_token
        new_name = "The token formerly known as Prince"
        res = self.app.patch_json_api(self.user1_token_url,
                             {'data': {'attributes':
                                  {'name': new_name},
                              'id': self.user1_token._id,
                              'type': 'tokens'
                             }}, auth=self.user1.auth, expect_errors=True)
        user1_token.reload()
        assert_equal(res.status_code, 200)

        assert_dict_contains_subset({'_id': user1_token._id,
                                     'owner': user1_token.owner._id,
                                     'name': new_name,
                                     'scopes': user1_token.scopes,
                                     },
                                    res.json['data']['attributes'])

    def test_updating_an_instance_does_not_change_the_number_of_instances(self):
        new_name = "The token formerly known as Prince"
        res = self.app.patch_json_api(self.user1_token_url,
                                      {'data': {
                                          'attributes': {"name": new_name},
                                          'id': self.user1_token._id,
                                          'type': 'tokens'}}, auth=self.user1.auth)
        assert_equal(res.status_code, 200)

        list_url = _get_token_list_url()
        res = self.app.get(list_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     1)

    # @mock.patch('framework.auth.cas.CasClient.revoke_personal_tokens')
    # def test_deleting_token_flags_instance_inactive(self, mock_method):
        # mock_method.return_value(True)
        # res = self.app.delete(self.user1_token_url, auth=self.user1.auth)
        # self.user1_token.reload()
        # assert_false(self.user1_token.is_active)

    def test_update_token(self):
        res = self.app.put_json_api(self.user1_token_url, self.correct, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_update_token_incorrect_type(self):
        res = self.app.put_json_api(self.user1_token_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_token_incorrect_id(self):
        res = self.app.put_json_api(self.user1_token_url, self.incorrect_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_token_no_type(self):
        res = self.app.put_json_api(self.user1_token_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_token_no_id(self):
        res = self.app.put_json_api(self.user1_token_url, self.missing_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_token_no_attributes(self):
        payload = {'id': self.user1_token._id, 'type': 'tokens', 'name': 'The token formerly known as Prince'}
        res = self.app.put_json_api(self.user1_token_url, payload, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_token_incorrect_type(self):
        res = self.app.patch_json_api(self.user1_token_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_token_incorrect_id(self):
        res = self.app.patch_json_api(self.user1_token_url, self.incorrect_id, auth=self.user1.auth, expect_errors=True)
        import ipdb; ipdb.set_trace()
        assert_equal(res.status_code, 409)

    def test_partial_update_token_no_type(self):
        res = self.app.patch_json_api(self.user1_token_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_token_no_id(self):
        res = self.app.patch_json_api(self.user1_token_url, self.missing_id, auth=self.user1.auth, expect_errors=True)
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
