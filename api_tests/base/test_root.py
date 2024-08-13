import itsdangerous
from unittest import mock
import unittest
from django.utils import timezone
from importlib import import_module
from django.conf import settings as django_conf_settings

from tests.base import ApiTestCase
from osf_tests.factories import (
    AuthUserFactory,
    ApiOAuth2ScopeFactory,
)

from api.base.settings.defaults import API_BASE

from framework.auth.cas import CasResponse
from website import settings
from osf.models import ApiOAuth2PersonalToken
from osf.utils.permissions import ADMIN

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.url = f'/{API_BASE}'

    def tearDown(self):
        self.app.reset()
        super().tearDown()

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user'] is None

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user']['data']['attributes']['given_name'] == self.user.given_name

    def test_current_user_accepted_tos(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user']['data']['attributes']['accepted_terms_of_service'] is False
        self.user.accepted_terms_of_service = timezone.now()
        self.user.save()
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['meta']['current_user']['data']['attributes']['accepted_terms_of_service'] is True

    def test_returns_302_redirect_for_base_url(self):
        res = self.app.get('/')
        assert res.status_code == 302
        assert res.location == '/v2/'

    def test_cookie_has_admin(self):
        session = SessionStore()
        session['auth_user_id'] = self.user._id
        session.create()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session.session_key).decode()
        self.app.set_cookie(settings.COOKIE_NAME, str(cookie))

        res = self.app.get(self.url)
        assert res.status_code == 200
        assert res.json['meta'][ADMIN] is True

    def test_basic_auth_does_not_have_admin(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert ADMIN not in res.json['meta'].keys()

    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @unittest.skipIf(
        not settings.DEV_MODE,
        'DEV_MODE disabled, osf.admin unavailable'
    )
    def test_admin_scoped_token_has_admin(self, mock_auth):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Admin Token',
        )
        token.save()
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.admin'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = self.user, mock_cas_resp
        res = self.app.get(
            self.url,
            headers={
                'Authorization': f'Bearer {token.token_id}'
            }
        )

        assert res.status_code == 200
        assert res.json['meta'][ADMIN] is True

    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    def test_non_admin_scoped_token_does_not_have_admin(self, mock_auth):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Admin Token',
        )
        token.save()
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.full_write'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = self.user, mock_cas_resp
        res = self.app.get(
            self.url,
            headers={
                'Authorization': f'Bearer {token.token_id}'
            }
        )

        assert res.status_code == 200
        assert ADMIN not in res.json['meta'].keys()
