# -*- coding: utf-8 -*-
import itsdangerous
import mock
from nose.tools import *  # noqa:
import unittest
from django.utils import timezone

from tests.base import ApiTestCase
from osf_tests.factories import (
    AuthUserFactory
)

from api.base.settings.defaults import API_BASE

from framework.auth.oauth_scopes import public_scopes
from framework.auth.cas import CasResponse
from website import settings
from osf.models import ApiOAuth2PersonalToken, Session


class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        super(TestWelcomeToApi, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}'.format(API_BASE)

    def tearDown(self):
        self.app.reset()
        super(TestWelcomeToApi, self).tearDown()

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user'], None)

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(
            res.json['meta']['current_user']['data']['attributes']['given_name'],
            self.user.given_name
        )

    def test_current_user_accepted_tos(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(
            res.json['meta']['current_user']['data']['attributes']['accepted_terms_of_service'],
            False
        )
        self.user.accepted_terms_of_service = timezone.now()
        self.user.save()
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(
            res.json['meta']['current_user']['data']['attributes']['accepted_terms_of_service'],
            True
        )

    def test_returns_302_redirect_for_base_url(self):
        res = self.app.get('/')
        assert_equal(res.status_code, 302)
        assert_equal(res.location, '/v2/')

    def test_cookie_has_admin(self):
        session = Session(data={'auth_user_id': self.user._id})
        session.save()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session._id)
        self.app.set_cookie(settings.COOKIE_NAME, str(cookie))

        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['admin'], True)

    def test_basic_auth_does_not_have_admin(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_not_in('admin', res.json['meta'].keys())

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
            scopes='osf.admin'
        )

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s for s in token.scopes.split(' ')]
            }
        )
        mock_auth.return_value = self.user, mock_cas_resp
        res = self.app.get(
            self.url,
            headers={
                'Authorization': 'Bearer {}'.format(token.token_id)
            }
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['admin'], True)

    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    def test_non_admin_scoped_token_does_not_have_admin(self, mock_auth):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Admin Token',
            scopes=' '.join([key for key in public_scopes if key != 'osf.admin'])
        )

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s for s in token.scopes.split(' ')]
            }
        )
        mock_auth.return_value = self.user, mock_cas_resp
        res = self.app.get(
            self.url,
            headers={
                'Authorization': 'Bearer {}'.format(token.token_id)
            }
        )

        assert_equal(res.status_code, 200)
        assert_not_in('admin', res.json['meta'].keys())
