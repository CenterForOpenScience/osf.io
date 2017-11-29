import copy
import mock
import pytest

from osf.models import ApiOAuth2PersonalToken
from osf_tests.factories import (
    ApiOAuth2PersonalTokenFactory,
    AuthUserFactory,
)
from website.util import api_v2_url
from website.util import sanitize

@pytest.mark.django_db
class TestTokenList:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def tokens_user_one(self, user_one):
        return [ApiOAuth2PersonalTokenFactory(owner=user_one) for i in xrange(3)]

    @pytest.fixture()
    def tokens_user_two(self, user_two):
        return [ApiOAuth2PersonalTokenFactory(owner=user_two) for i in xrange(3)]

    @pytest.fixture()
    def url_token_list(self):
        return api_v2_url('tokens/', base_route='/')

    @pytest.fixture()
    def data_sample(self):
        return {
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

    def test_user_one_should_see_only_their_tokens(self, app, url_token_list, user_one, tokens_user_one):
        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one))

    def test_user_two_should_see_only_their_tokens(self, app, url_token_list, user_two, tokens_user_two):
        res = app.get(url_token_list, auth=user_two.auth)
        assert (len(res.json['data']) == len(tokens_user_two))

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_should_hide_it_from_api_list(self, mock_method, app, user_one, tokens_user_one, url_token_list):
        mock_method.return_value(True)
        api_token = tokens_user_one[0]
        url = api_v2_url('tokens/{}/'.format(api_token._id), base_route='/')

        res = app.delete(url, auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(url_token_list, auth=user_one.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == len(tokens_user_one) - 1)

    def test_created_tokens_are_tied_to_request_user_with_data_specified(self, app, url_token_list, data_sample, user_one):
        res = app.post_json_api(url_token_list, data_sample, auth=user_one.auth)
        assert res.status_code == 201

        assert res.json['data']['attributes']['owner'] == user_one._id
        # Some fields aren't writable; make sure user can't set these
        assert (res.json['data']['attributes']['token_id'] != data_sample['data']['attributes']['token_id'])

    def test_create_returns_token_id(self, app, url_token_list, data_sample, user_one):
        res = app.post_json_api(url_token_list, data_sample, auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes'].has_key('token_id')

    def test_field_content_is_sanitized_upon_submission(self, app, data_sample, user_one, url_token_list):
        bad_text = '<a href="http://sanitized.name">User_text</a>'
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.deepcopy(data_sample)
        payload['data']['attributes']['name'] = bad_text

        res = app.post_json_api(url_token_list, payload, auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == cleaned_text

    def test_created_tokens_show_up_in_api_list(self, app, url_token_list, data_sample, user_one, tokens_user_one):
        res = app.post_json_api(url_token_list, data_sample, auth=user_one.auth)
        assert res.status_code == 201

        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one) + 1)

    def test_returns_401_when_not_logged_in(self, app, url_token_list):
        res = app.get(url_token_list, expect_errors=True)
        assert res.status_code == 401

    def test_cannot_create_admin_token(self, app, url_token_list, data_sample, user_one):
        data_sample['data']['attributes']['scopes'] = 'osf.admin'
        res = app.post_json_api(url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User requested invalid scope'

    def test_cannot_create_usercreate_token(self, app, url_token_list, data_sample, user_one):
        data_sample['data']['attributes']['scopes'] = 'osf.users.create'
        res = app.post_json_api(url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User requested invalid scope'
