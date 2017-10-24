# -*- coding: utf-8 -*-
import itsdangerous
import mock
import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.oauth_scopes import public_scopes
from framework.auth.cas import CasResponse
from osf_tests.factories import AuthUserFactory
from osf.models import ApiOAuth2PersonalToken, Session
from website import settings


@pytest.mark.django_db
class TestWelcomeToApi:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self):
        return '/{}'.format(API_BASE)

    def test_returns_200_for_logged_out_user(self, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user'] is None

    def test_returns_current_user_info_when_logged_in(self, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user']['data']['attributes']['given_name'] == user.given_name

    def test_returns_302_redirect_for_base_url(self, app):
        res = app.get('/')
        assert res.status_code == 302
        assert res.location == '/v2/'

    def test_cookie_has_admin(self, app, user, url):
        session = Session(data={'auth_user_id': user._id})
        session.save()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session._id)
        app.set_cookie(settings.COOKIE_NAME, str(cookie))

        res = app.get(url)
        assert res.status_code == 200
        assert res.json['meta']['admin'] is True

    def test_basic_auth_does_not_have_admin(self, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert 'admin' not in res.json['meta'].keys()

    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @pytest.mark.skipif(not settings.DEV_MODE,
                        reason='DEV_MODE disabled, osf.admin unavailable')
    def test_admin_scoped_token_has_admin(self, mock_auth, app, url, user):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Admin Token',
            scopes='osf.admin'
        )

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s for s in token.scopes.split(' ')]
            }
        )
        mock_auth.return_value = user, mock_cas_resp
        res = app.get(
            url, headers={
                'Authorization': 'Bearer {}'.format(
                    token.token_id)})

        assert res.status_code == 200
        assert res.json['meta']['admin'] is True

    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    def test_non_admin_scoped_token_does_not_have_admin(
            self, mock_auth, app, url, user):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Admin Token',
            scopes=' '.join([key for key in public_scopes if key != 'osf.admin'])
        )

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s for s in token.scopes.split(' ')]
            }
        )
        mock_auth.return_value = user, mock_cas_resp
        res = app.get(
            url, headers={
                'Authorization': 'Bearer {}'.format(
                    token.token_id)})

        assert res.status_code == 200
        assert 'admin' not in res.json['meta'].keys()
