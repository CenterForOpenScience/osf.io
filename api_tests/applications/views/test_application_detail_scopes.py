from unittest import mock

import pytest

from framework.auth.cas import CasResponse
from website.util import api_v2_url
from osf_tests.factories import (
    ApiOAuth2ApplicationFactory,
    ApiOAuth2PersonalTokenFactory,
    ApiOAuth2ScopeFactory,
    AuthUserFactory,
)

@pytest.mark.django_db
class TestApplicationScopes:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_scope(self):
        return ApiOAuth2ScopeFactory(name='osf.full_write')

    @pytest.fixture()
    def token_full_write(self, user, write_scope):
        token = ApiOAuth2PersonalTokenFactory(
            owner=user,
        )
        token.scopes.add(write_scope)
        assert token.owner == user
        return token

    def _get_application_list_url(self):
        return api_v2_url('applications/', base_route='/')

    def make_payload(self, user_app):
        return {
            'data': {
                'id': user_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'Updated application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'http://osf.io',
                }
            }
        }

    @pytest.fixture
    def user_app(self, user):
        oauth_app = ApiOAuth2ApplicationFactory(owner=user)
        assert user == oauth_app.owner
        return oauth_app

    @pytest.fixture
    def user_app_url(self, user_app):
        return api_v2_url(f'applications/{user_app.client_id}/', base_route='/')

    @pytest.fixture
    def user_app_list_url(self):
        return self._get_application_list_url()

    def test_can_update_with_full_write_scope(self, app, user, user_app, token_full_write, user_app_url):
        with mock.patch('framework.auth.cas.CasClient.profile') as mock_cas:
            mock_cas.return_value = CasResponse(
                authenticated=True,
                user=user._id,
                attributes={'accessTokenScope': ['osf.full_write',]}
            )
            res = app.put_json_api(
                user_app_url,
                self.make_payload(user_app),
                headers={'Authorization': f'Bearer {token_full_write.token_id}'},
                expect_errors=True
            )
        assert res.status_code == 200
