from __future__ import absolute_import
from rest_framework import status as http_status
import pytest
from nose.tools import assert_equal
from framework.auth import Auth
from framework.auth.views import login_and_register_handler
from website.util import web_url_for
from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, InstitutionFactory

pytestmark = pytest.mark.django_db


class TestAuthLoginAndRegisterLogic(OsfTestCase):

    def setUp(self):
        super(TestAuthLoginAndRegisterLogic, self).setUp()

        self.user_auth = AuthUserFactory()
        self.auth = Auth(user=self.user_auth)
        self.next_url = web_url_for('my_projects', _absolute=True)

    def test_osf_login_with_institutional_auth(self):
        institution = InstitutionFactory()
        self.user_auth.affiliated_institutions.add(institution)
        self.user_auth.family_name_ja = ''
        self.user_auth.save()
        self.auth = Auth(user=self.user_auth)
        data = login_and_register_handler(self.auth)
        assert_equal(data.get('status_code'), http_status.HTTP_302_FOUND)
        assert_equal(data.get('next_url'), web_url_for('user_profile',
                                                       _absolute=True))
