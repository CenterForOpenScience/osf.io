# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    AuthUserFactory
)


class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        super(TestWelcomeToApi, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}'.format(API_BASE)

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user'], None)

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user']['data']['attributes']['given_name'], self.user.given_name)

    def test_returns_302_redirect_for_base_url(self):
        res = self.app.get('/')
        assert_equal(res.status_code, 302)
        assert_equal(res.location, '/v2/')
