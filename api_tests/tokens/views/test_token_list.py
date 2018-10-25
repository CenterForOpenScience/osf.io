import copy
import mock
import pytest

from osf_tests.factories import (
    ApiOAuth2PersonalTokenFactory,
    ApiOAuth2ScopeFactory,
    AuthUserFactory,
)
from osf.models.oauth import ApiOAuth2PersonalToken
from website.util import api_v2_url
from osf.utils import sanitize


@pytest.mark.django_db
class TestTokenListScopesasRelationships:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def tokens_user_one(self, user_one):
        return [ApiOAuth2PersonalTokenFactory(
            owner=user_one) for i in range(3)]

    @pytest.fixture()
    def tokens_user_two(self, user_two):
        return [ApiOAuth2PersonalTokenFactory(
            owner=user_two) for i in range(3)]

    @pytest.fixture()
    def url_token_list(self):
        return api_v2_url('tokens/?version=2.11', base_route='/')

    @pytest.fixture()
    def read_scope(self):
        return ApiOAuth2ScopeFactory()

    @pytest.fixture()
    def data_sample(self, read_scope):
        return {
            'data': {
                'type': 'tokens',
                'attributes': {
                    'name': 'A shiny new token',
                    'token_id': 'Value discarded',
                },
                'relationships': {
                    'scopes': {
                        'data': [{
                            'type': 'scopes',
                            'id': read_scope.name
                        }]
                    }
                }
            }
        }

    def test_user_one_should_see_only_their_tokens(
            self, app, url_token_list, user_one, tokens_user_one):
        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one))
        assert 'scopes' in res.json['data'][0]['relationships']
        assert 'scopes' not in res.json['data'][0]['attributes']

    def test_user_two_should_see_only_their_tokens(
            self, app, url_token_list, user_two, tokens_user_two):
        res = app.get(url_token_list, auth=user_two.auth)
        assert (len(res.json['data']) == len(tokens_user_two))
        assert 'scopes' in res.json['data'][0]['relationships']
        assert 'scopes' not in res.json['data'][0]['attributes']

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_should_hide_it_from_api_list(
            self, mock_method, app, user_one, tokens_user_one, url_token_list):
        mock_method.return_value(True)
        api_token = tokens_user_one[0]
        url = api_v2_url('tokens/{}/'.format(api_token._id), base_route='/')

        res = app.delete(url, auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(url_token_list, auth=user_one.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == len(tokens_user_one) - 1)
        assert 'scopes' in res.json['data'][0]['relationships']
        assert 'scopes' not in res.json['data'][0]['attributes']
    #
    def test_created_tokens_are_tied_to_request_user_with_data_specified(
            self, app, url_token_list, data_sample, user_one, read_scope):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201

        assert res.json['data']['relationships']['owner']['data']['id'] == user_one._id
        assert len(res.json['data']['embeds']['scopes']['data']) == 1
        assert res.json['data']['embeds']['scopes']['data'][0]['id'] == read_scope.name
        assert 'scopes' in res.json['data']['relationships']
        assert 'scopes' not in res.json['data']['attributes']
        # Some fields aren't writable; make sure user can't set these
        assert (res.json['data']['attributes']['token_id'] !=
                data_sample['data']['attributes']['token_id'])

    def test_create_returns_token_id(
            self, app, url_token_list, data_sample, user_one):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201
        assert 'token_id' in res.json['data']['attributes']
        assert 'scopes' in res.json['data']['relationships']
        assert 'scopes' not in res.json['data']['attributes']

    def test_field_content_is_sanitized_upon_submission(
            self, app, data_sample, user_one, url_token_list):
        bad_text = '<a href="http://sanitized.name">User_text</a>'
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.deepcopy(data_sample)
        payload['data']['attributes']['name'] = bad_text

        res = app.post_json_api(url_token_list, payload, auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == cleaned_text
        assert 'scopes' in res.json['data']['relationships']
        assert 'scopes' not in res.json['data']['attributes']

    def test_created_tokens_show_up_in_api_list(
            self, app, url_token_list, data_sample, user_one, tokens_user_one):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one) + 1)
        assert 'scopes' in res.json['data'][0]['relationships']
        assert 'scopes' not in res.json['data'][0]['attributes']

    def test_returns_401_when_not_logged_in(self, app, url_token_list):
        res = app.get(url_token_list, expect_errors=True)
        assert res.status_code == 401

    def test_cannot_create_token_with_nonexistant_scope(
            self, app, url_token_list, data_sample, user_one):
        data_sample['data']['relationships']['scopes']['data'][0]['id'] = 'osf.admin'
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_cannot_create_token_with_private_scope(
            self, app, url_token_list, data_sample, user_one):
        scope = ApiOAuth2ScopeFactory()
        scope.is_public = False
        scope.save()
        data_sample['data']['relationships']['scopes']['data'][0]['id'] = scope.name
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User requested invalid scope'

    def test_add_multiple_scopes_when_creating_token(
            self, app, url_token_list, data_sample, user_one, read_scope):
        write_scope = ApiOAuth2ScopeFactory()
        data_sample['data']['relationships']['scopes']['data'].append(
            {
                'type': 'scopes',
                'id': write_scope.name
            }
        )
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 201
        assert len(res.json['data']['embeds']['scopes']['data']) == 2
        assert res.json['data']['embeds']['scopes']['data'][0]['id'] == read_scope.name
        assert res.json['data']['embeds']['scopes']['data'][1]['id'] == write_scope.name
        assert 'scopes' in res.json['data']['relationships']
        assert 'scopes' not in res.json['data']['attributes']
        token = ApiOAuth2PersonalToken.objects.get(_id=res.json['data']['id'])
        assert len(token.scopes.all()) == 2
        token_scope_names = [scope.name for scope in token.scopes.all()]
        assert read_scope.name in token_scope_names
        assert write_scope.name in token_scope_names


@pytest.mark.django_db
class TestTokenListScopesAsAttributes:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def tokens_user_one(self, user_one):
        return [ApiOAuth2PersonalTokenFactory(
            owner=user_one) for i in range(3)]

    @pytest.fixture()
    def tokens_user_two(self, user_two):
        return [ApiOAuth2PersonalTokenFactory(
            owner=user_two) for i in range(3)]

    @pytest.fixture()
    def url_token_list(self):
        return api_v2_url('tokens/', base_route='/')

    @pytest.fixture()
    def write_token(self):
        return ApiOAuth2ScopeFactory(name='osf.full_write')

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

    def test_user_one_should_see_only_their_tokens(
            self, app, url_token_list, user_one, tokens_user_one):
        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one))
        assert 'scopes' in res.json['data'][0]['attributes']

    def test_user_two_should_see_only_their_tokens(
            self, app, url_token_list, user_two, tokens_user_two):
        res = app.get(url_token_list, auth=user_two.auth)
        assert (len(res.json['data']) == len(tokens_user_two))
        assert 'scopes' in res.json['data'][0]['attributes']

    @mock.patch('framework.auth.cas.CasClient.revoke_tokens')
    def test_deleting_token_should_hide_it_from_api_list(
            self, mock_method, app, user_one, tokens_user_one, url_token_list):
        mock_method.return_value(True)
        api_token = tokens_user_one[0]
        url = api_v2_url('tokens/{}/'.format(api_token._id), base_route='/')

        res = app.delete(url, auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(url_token_list, auth=user_one.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == len(tokens_user_one) - 1)
        assert 'scopes' in res.json['data'][0]['attributes']

    def test_created_tokens_are_tied_to_request_user_with_data_specified(
            self, app, url_token_list, data_sample, user_one, write_token):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201

        assert res.json['data']['attributes']['owner'] == user_one._id
        assert write_token.name in res.json['data']['attributes']['scopes']
        # Some fields aren't writable; make sure user can't set these
        assert (res.json['data']['attributes']['token_id'] !=
                data_sample['data']['attributes']['token_id'])

    def test_create_returns_token_id(
            self, app, url_token_list, data_sample, user_one, write_token):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201
        assert 'token_id' in res.json['data']['attributes']
        assert write_token.name in res.json['data']['attributes']['scopes']

    def test_field_content_is_sanitized_upon_submission(
            self, app, data_sample, user_one, url_token_list, write_token):
        bad_text = '<a href="http://sanitized.name">User_text</a>'
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.deepcopy(data_sample)
        payload['data']['attributes']['name'] = bad_text

        res = app.post_json_api(url_token_list, payload, auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == cleaned_text
        assert write_token.name in res.json['data']['attributes']['scopes']

    def test_created_tokens_show_up_in_api_list(
            self, app, url_token_list, data_sample, user_one, tokens_user_one, write_token):
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get(url_token_list, auth=user_one.auth)
        assert (len(res.json['data']) == len(tokens_user_one) + 1)
        assert write_token.name in res.json['data'][0]['attributes']['scopes']

    def test_returns_401_when_not_logged_in(self, app, url_token_list):
        res = app.get(url_token_list, expect_errors=True)
        assert res.status_code == 401

    def test_cannot_create_admin_token(
            self, app, url_token_list, data_sample, user_one):
        data_sample['data']['attributes']['scopes'] = 'osf.admin'
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_cannot_create_usercreate_token(
            self, app, url_token_list, data_sample, user_one):
        scope = ApiOAuth2ScopeFactory(name='osf.users.create')
        scope.is_public = False
        scope.save()
        data_sample['data']['attributes']['scopes'] = 'osf.users.create'
        res = app.post_json_api(
            url_token_list,
            data_sample,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User requested invalid scope'
