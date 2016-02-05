import copy
import mock

from nose.tools import * # flake8: noqa

from website.models import User, ApiOAuth2PersonalToken
from website.util import api_v2_url
from website.util import sanitize

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2PersonalTokenFactory, AuthUserFactory

TOKEN_LIST_URL = api_v2_url('tokens/', base_route='/')

def _get_token_detail_route(token):
    path = "tokens/{}/".format(token._id)
    return api_v2_url(path, base_route='/')


class TestTokenList(ApiTestCase):
    def setUp(self):
        super(TestTokenList, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_tokens = [ApiOAuth2PersonalTokenFactory(owner=self.user1) for i in xrange(3)]
        self.user2_tokens = [ApiOAuth2PersonalTokenFactory(owner=self.user2) for i in xrange(2)]

        self.user1_list_url = TOKEN_LIST_URL
        self.user2_list_url = TOKEN_LIST_URL

        self.sample_data = {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny new token',
                    'scopes': 'osf.full_write',
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

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_should_hide_it_from_api_list(self, mock_method):
        mock_method.return_value(True)
        api_token = self.user1_tokens[0]
        url = _get_token_detail_route(api_token)

        res = self.app.delete(url, auth=self.user1.auth)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     len(self.user1_tokens) - 1)

    def test_created_tokens_are_tied_to_request_user_with_data_specified(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth)
        assert_equal(res.status_code, 201)

        assert_equal(res.json['data']['attributes']['owner'], self.user1._id)
        # Some fields aren't writable; make sure user can't set these
        assert_not_equal(res.json['data']['attributes']['token_id'],
                         self.sample_data['data']['attributes']['token_id'])

    def test_create_returns_token_id(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth)
        assert_equal(res.status_code, 201)
        assert_true(res.json['data']['attributes'].has_key('token_id'))

    def test_field_content_is_sanitized_upon_submission(self):
        bad_text = "<a href='http://sanitized.name'>User_text</a>"
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.deepcopy(self.sample_data)
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
