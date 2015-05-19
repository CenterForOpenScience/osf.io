# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa (PEP8 asserts)
from werkzeug.wrappers import BaseResponse

from framework import sessions
from framework.auth import authenticate_two_factor, verify_two_factor, user_requires_two_factor_verification
from framework.auth.exceptions import TwoFactorValidationError
from tests.base import OsfTestCase
from tests.factories import UserFactory
from website.app import init_app
from website.addons.twofactor.tests import _valid_code
from website.util import web_url_for

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
        self.user.save()

        self.user.add_addon('twofactor')
        self.user_settings = self.user.get_addon('twofactor')

        self.user_settings.is_confirmed = True
        self.user_settings.save()

    def test_authenticate_two_factor_returns_correct_response(self):
        response = authenticate_two_factor(self.user)
        assert_true(isinstance(response, BaseResponse))
        assert_equal(response.location, web_url_for('two_factor'))
        assert_equal(response.status_code, 302)

    def test_authenticate_two_factor_with_next_url(self):
        fake_session = sessions.Session(data={'next_url': '/someendpoint/'})
        sessions.set_session(fake_session)

        response = authenticate_two_factor(self.user)
        assert_true(isinstance(response, BaseResponse))

        assert_equal(response.location,
                     u'{0}?next=%2Fsomeendpoint%2F'.format(web_url_for('two_factor'))
        )
        assert_equal(response.status_code, 302)

    def test_verify_two_factor_with_invalid_code(self):
        with assert_raises(TwoFactorValidationError):
            verify_two_factor(self.user._id, 1234567)

    def test_verify_two_factor_with_valid_code(self):
        fake_session = sessions.Session(data={
            'two_factor_auth':{
                'auth_user_username': self.user.username,
                'auth_user_id': self.user._primary_key,
                'auth_user_fullname': self.user.fullname,
            }
        })
        sessions.set_session(fake_session)
        response = verify_two_factor(self.user._id,
                                     _valid_code(self.user_settings.totp_secret)
        )
        assert_true(isinstance(response, BaseResponse))
        assert_equal(response.location, u'/dashboard/')
        assert_equal(response.status_code, 302)

    def test_verify_two_factor_with_valid_code_and_next_url(self):
        fake_session = sessions.Session(data={
            'two_factor_auth':{
                'auth_user_username': self.user.username,
                'auth_user_id': self.user._primary_key,
                'auth_user_fullname': self.user.fullname,
            },
            'next_url': '/someendpoint/'
        })
        sessions.set_session(fake_session)
        response = verify_two_factor(self.user._id,
                                     _valid_code(self.user_settings.totp_secret)
        )
        assert_true(isinstance(response, BaseResponse))
        assert_equal(response.location, u'/someendpoint/')
        assert_equal(response.status_code, 302)

    def test_user_requires_two_factor_verification_returns_true_if_confirmed(self):
        response = user_requires_two_factor_verification(self.user)
        assert_true(response)

    def test_user_requires_two_factor_verification_returns_false_if_not_confirmed(self):
        self.user_settings.is_confirmed = False
        response = user_requires_two_factor_verification(self.user)
        assert_false(response)
