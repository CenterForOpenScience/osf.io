import pytest

from osf_tests.factories import (
    FlagFactory,
)

from tests.json_api_test_app import JSONAPITestApp
from tests.base import OsfTestCase


@pytest.mark.django_db
class TestWaffleCookies(OsfTestCase):

    def setUp(self):
        super(TestWaffleCookies, self).setUp()
        self.flag = FlagFactory(name='test_flag')
        self.flag.percent = 50
        self.flag.everyone = None
        self.flag.save()

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
        waffle_cookie = [value for key, value in list(resp.headers.items()) if 'dwf_test_flag' in value][0]

        cookie_str = 'dwf_test_flag={};'

        assert cookie_str.format('True') in waffle_cookie or cookie_str.format('False') in waffle_cookie
