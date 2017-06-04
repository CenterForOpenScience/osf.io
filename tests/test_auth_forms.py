# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts
from wtforms import Form, Field

from framework.auth import forms

from tests.base import OsfTestCase
from tests.factories import UserFactory, UnregUserFactory


class TestValidation(OsfTestCase):

    def test_unique_email_validator(self):
        class MockForm(Form):
            username = Field('Username', [forms.UniqueEmail()])
        u = UserFactory()
        f = MockForm(username=u.username)
        f.validate()
        assert_in('username', f.errors)

    def test_unique_email_validator_with_unreg_user(self):
        class MockForm(Form):
            username = Field(
                'Username',
                [forms.UniqueEmail(allow_unregistered=True)]
            )
        u = UnregUserFactory()
        f = MockForm(username=u.username)
        assert_true(f.validate())
