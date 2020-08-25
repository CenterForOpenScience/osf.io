import mock
import pytest
from functools import wraps

from osf_tests.factories import (
    AuthUserFactory,
    FlagFactory,
    ProjectFactory
)
from website.project.views.node import _view_project

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
