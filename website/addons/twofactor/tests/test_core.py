# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)
from werkzeug.wrappers import BaseResponse

from framework.auth import login
from framework.auth.exceptions import PasswordIncorrectError, TwoFactorValidationError
from tests.base import OsfTestCase
from tests.factories import UserFactory
from website.app import init_app
from website.addons.twofactor.tests import _valid_code

app = init_app(
    routes=True,
    set_backends=False,
    settings_module='website.settings',
)


class TestCore(OsfTestCase):
    @mock.patch('website.addons.twofactor.models.push_status_message')
    def setUp(self, mocked):
        super(TestCore, self).setUp()
        self.user = UserFactory()
        self.user.set_password('badpassword')
        self.user.save()

        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

        self.user_settings.is_confirmed = True
        self.user_settings.save()

    def test_login_valid(self):
        res = login(
            username=self.user.username,
            password='badpassword',
            two_factor=_valid_code(self.user_settings.totp_secret)
        )
        assert_true(isinstance(res, BaseResponse))
        assert_equal(res.status_code, 302)

    def test_login_invalid_code(self):
        with assert_raises(TwoFactorValidationError):
            login(
                username=self.user.username,
                password='badpassword',
                two_factor='000000'
            )

    def test_login_valid_code_invalid_password(self):
        with assert_raises(PasswordIncorrectError):
            login(
                username=self.user.username,
                password='notmypasswordman...',
                two_factor=_valid_code(self.user_settings.totp_secret)
            )
