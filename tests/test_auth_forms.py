# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts
from wtforms import Form, Field

from framework.auth import forms

from tests.base import OsfTestCase
from tests.factories import UserFactory, UnregUserFactory


def test_registration_form_processing():
    form = forms.RegistrationForm(
        fullname='Freddy Mercury   \t',
        username=' fRed@queen.com  ',
        username2='fRed@queen.com',
        password='killerqueen ',
        password2='killerqueen'
    )
    assert_equal(form.fullname.data, 'Freddy Mercury')
    assert_equal(form.username.data, 'fred@queen.com')
    assert_equal(form.username2.data, 'fred@queen.com')
    assert_equal(form.password.data, 'killerqueen')
    assert_equal(form.password2.data, 'killerqueen')


def test_merge_account_form_cleaning():
    form = forms.MergeAccountForm(
        merged_username='freD@queen.com\t ',
        merged_password='rhapsodY123 ',
        user_password='bohemi1aN '
    )
    assert_equal(form.merged_username.data, 'fred@queen.com')
    assert_equal(form.merged_password.data, 'rhapsodY123')
    assert_equal(form.user_password.data, 'bohemi1aN')


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
