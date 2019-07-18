import mock
import pytest
from functools import wraps

from osf_tests.factories import (
    AuthUserFactory,
    FlagFactory,
    ProjectFactory
)
from website.project.views.node import _view_project

from tests.json_api_test_app import JSONAPITestApp
from tests.base import OsfTestCase

from api.waffle.utils import flag_is_active


def inject_check_is_active(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        from flask import request
        flag_is_active(request, 'test_flag')
        return func(self, *args, **kwargs)
    return wrapped


@pytest.mark.django_db
class TestWaffleCookies(OsfTestCase):

    def setUp(self):
        super(TestWaffleCookies, self).setUp()
        self.flag = FlagFactory(name='test_flag')
        self.flag.percent = 50
        self.flag.everyone = None
        self.flag.save()

    @pytest.mark.enable_bookmark_creation
    @mock.patch('website.project.views.node._view_project', inject_check_is_active(_view_project))
    def test_waffle_leaves_cookie(self):
        """
        Tests that django-waffle cookies work in the with our Flask requests. We inject an is_active test here so we
        don't break the tests when adding/removing flags.

        Flask waffle cookies are formatted:
        `dwf_test_flag=True; Expires=True; Max-Age=2592000; Path=/`

        """
        node = ProjectFactory(is_public=True)
        user = AuthUserFactory()
        resp = self.app.get(node.web_url_for('view_project'), auth=user.auth, auto_follow=True)

        waffle_cookie = next(value for key, value in list(resp.headers.items()) if 'dwf_test_flag=' in value)

        cookie_str = 'dwf_test_flag={}; Expires=True; Max-Age=2592000; Path=/'

        assert waffle_cookie == cookie_str.format('True') or waffle_cookie == cookie_str.format('False')

    @pytest.mark.enable_bookmark_creation
    def test_waffle_v2_root_leaves_cookie(self):
        """
        Tests that django-waffle cookies work in the with our Flask requests. Don't need to inject here because the /v2/
        root view already checks if all flags in the DB are active and this the only route  the ember front-end uses
        for cookies.

        DRF waffle cookies are formatted:
        `dwf_test_flag=True; expires=Fri, 09-Aug-2019 16:33:52 GMT; Max-Age=2592000; Path=/; secure`

        """
        app = JSONAPITestApp()
        resp = app.get('/v2/')
        waffle_cookie = next(value for key, value in list(resp.headers.items()) if key == 'Set-Cookie')

        cookie_str = 'dwf_test_flag={};'

        assert cookie_str.format('True') in waffle_cookie or cookie_str.format('False') in waffle_cookie
