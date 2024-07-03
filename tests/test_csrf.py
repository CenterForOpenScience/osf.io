from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory
from django.conf import settings as api_settings
from website import settings


class TestCSRF(OsfTestCase):

    def test_csrf_cookie_gets_set_on_authd_request(self):
        user = AuthUserFactory()
        # use session auth
        session_cookie = user.get_or_create_cookie()
        self.app.set_cookie(settings.COOKIE_NAME, session_cookie.decode())
        res = self.app.get('/settings/', auth=user.auth)
        assert res.status_code == 200
        assert api_settings.CSRF_COOKIE_NAME in self.app.cookies
