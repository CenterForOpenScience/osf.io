import pytest

from osf_tests.factories import (
    ApiOAuth2PersonalTokenFactory,
    ApiOAuth2ScopeFactory,
    AuthUserFactory,
)
from website.util import api_v2_url

@pytest.mark.django_db
class TestTokenScopes:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def token_user_one(self, user_one, read_scope):
        token = ApiOAuth2PersonalTokenFactory(owner=user_one)
        token.scopes.add(read_scope)
        return token

    @pytest.fixture()
    def url_token_scopes_list(self, token_user_one):
        return api_v2_url('tokens/{}/scopes/?version=2.11'.format(token_user_one._id), base_route='/')

    @pytest.fixture()
    def read_scope(self):
        return ApiOAuth2ScopeFactory()

    def test_user_token_scopes(self, app, url_token_scopes_list, user_one, user_two, read_scope):
        # Authenticated, current user scopes
        res = app.get(url_token_scopes_list, auth=user_one.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert read_scope.name in [scope['id'] for scope in data]

        # Authenticated, accessing another's scopes
        res = app.get(url_token_scopes_list, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Unauthenticated
        res = app.get(url_token_scopes_list, expect_errors=True)
        assert res.status_code == 401

        # Token not found
        url = api_v2_url('tokens/{}/scopes/?version=2.11'.format('bad_token'), base_route='/')
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404
