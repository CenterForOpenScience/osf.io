# -*- coding: utf-8 -*-
import itsdangerous
import mock
from nose.tools import *  # flake8: noqa
import unittest
import urlparse

from modularodm import Q

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory

from api.base.settings.defaults import API_BASE

from framework.auth.cas import CasResponse
from framework.sessions.model import Session
from website.models import User
from website import settings
from website.oauth.models import ApiOAuth2PersonalToken


class TestUsers(ApiTestCase):

    def setUp(self):
        super(TestUsers, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()

    def tearDown(self):
        super(TestUsers, self).tearDown()

    def test_returns_200(self):
        res = self.app.get('/{}users/'.format(API_BASE))
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_find_user_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/{}users/".format(API_BASE)

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/{}users/?filter[full_name]=fred".format(API_BASE)

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/{}users/?filter[full_name]=my".format(API_BASE)
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/{}users/?filter[full_name]=NotMyMom".format(API_BASE)
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_users_list_takes_profile_image_size_param(self):
        size = 42
        url = "/{}users/?profile_image_size={}".format(API_BASE, size)
        res = self.app.get(url)
        user_json = res.json['data']
        for user in user_json:
            profile_image_url = user['links']['profile_image']
            query_dict = urlparse.parse_qs(urlparse.urlparse(profile_image_url).query)
            assert_equal(int(query_dict.get('s')[0]), size)

class TestUsersCreate(ApiTestCase):

    def setUp(self):
        super(TestUsersCreate, self).setUp()
        self.user = AuthUserFactory()
        self.unconfirmed_email = 'tester@fake.io'
        self.base_url = '/{}users/'.format(API_BASE)
        self.data = {
            'data': {
                'type': 'users',
                'attributes': {
                    'username': self.unconfirmed_email,
                    'full_name': 'Test Account'
                }
            }
        }

    def tearDown(self):
        super(TestUsersCreate, self).tearDown()
        self.app.reset()  # clears cookies
        User.remove()

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_user_can_not_create_other_user_or_send_mail(self, mock_mail):
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            '{}?send_email=true'.format(self.base_url),
            self.data,
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cookied_requests_do_not_create_or_email(self, mock_mail):
        session = Session(data={'auth_user_id': self.user._id})
        session.save()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session._id)
        self.app.set_cookie(settings.COOKIE_NAME, str(cookie))

        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            self.base_url,
            self.data,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    @unittest.skipIf(not settings.DEV_MODE, 'DEV_MODE disabled, osf.users.create unavailable')  # TODO: Remove when available outside of DEV_MODE
    def test_properly_scoped_token_can_create_and_send_email(self, mock_auth, mock_mail):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Authorized Token',
            scopes='osf.users.create'
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

        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            '{}?send_email=true'.format(self.base_url),
            self.data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['username'], self.unconfirmed_email)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 1)
        assert_equal(mock_mail.call_count, 1)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    @unittest.skipIf(not settings.DEV_MODE, 'DEV_MODE disabled, osf.users.create unavailable')  # TODO: Remove when available outside of DEV_MODE
    def test_properly_scoped_token_does_not_send_email_without_kwarg(self, mock_auth, mock_mail):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Authorized Token',
            scopes='osf.users.create'
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

        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            self.base_url,
            self.data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['username'], self.unconfirmed_email)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 1)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    @unittest.skipIf(not settings.DEV_MODE, 'DEV_MODE disabled, osf.users.create unavailable')  # TODO: Remove when available outside of DEV_MODE
    def test_properly_scoped_token_can_create_without_username_but_not_send_email(self, mock_auth, mock_mail):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Authorized Token',
            scopes='osf.users.create'
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

        self.data['data']['attributes'] = {'full_name': 'No Email'}

        assert_equal(User.find(Q('fullname', 'eq', 'No Email')).count(), 0)
        res = self.app.post_json_api(
            '{}?send_email=true'.format(self.base_url),
            self.data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['username'], None)
        assert_equal(User.find(Q('fullname', 'eq', 'No Email')).count(), 1)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    def test_improperly_scoped_token_can_not_create_or_email(self, mock_auth, mock_mail):
        token = ApiOAuth2PersonalToken(
            owner=self.user,
            name='Unauthorized Token',
            scopes='osf.full_write'
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

        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            '{}?send_email=true'.format(self.base_url),
            self.data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)},
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    @unittest.skipIf(not settings.DEV_MODE, 'DEV_MODE disabled, osf.admin unavailable')  # TODO: Remove when available outside of DEV_MODE
    def test_admin_scoped_token_can_create_and_send_email(self, mock_auth, mock_mail):
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

        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 0)
        res = self.app.post_json_api(
            '{}?send_email=true'.format(self.base_url),
            self.data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['username'], self.unconfirmed_email)
        assert_equal(User.find(Q('username', 'eq', self.unconfirmed_email)).count(), 1)
        assert_equal(mock_mail.call_count, 1)
