from http.cookies import SimpleCookie

import pytest
from flask import Flask, Response

from framework.csrf import handlers
from tests.base import OsfTestCase
from osf_tests.factories import UserFactory
from django.conf import settings as api_settings
from website import settings


class TestCSRFHandlers:

    @pytest.mark.parametrize('secure', [False, True])
    def test_csrf_cookie_flags(self, settings, monkeypatch, secure):
        settings.CSRF_COOKIE_SECURE = secure
        monkeypatch.setattr(handlers, 'get_current_user_id', lambda: 'user')
        app = Flask(__name__)

        with app.test_request_context('/'):
            handlers.before_request()
            response = handlers.after_request(Response())

        cookies = SimpleCookie()
        cookies.load(response.headers['Set-Cookie'])
        cookie = cookies[api_settings.CSRF_COOKIE_NAME]
        assert bool(cookie['secure']) == secure
        assert not cookie['httponly']


class TestCSRF(OsfTestCase):

    def test_csrf_cookie_gets_set_on_authd_request(self):
        user = UserFactory()
        # use session auth
        session_cookie = user.get_or_create_cookie()
        self.app.set_cookie(settings.COOKIE_NAME, session_cookie.decode())
        res = self.app.get('/settings/')
        assert res.status_code == 200
        assert self.app.get_cookie(api_settings.CSRF_COOKIE_NAME)
