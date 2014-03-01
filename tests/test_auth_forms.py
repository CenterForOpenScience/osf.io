# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts

from framework.auth.forms import RegistrationForm, MergeAccountForm


def test_registration_form_processing():
    form = RegistrationForm(fullname='Freddy Mercury   \t',
        username=' fRed@queen.com  ',
        username2='fRed@queen.com',
        password='killerqueen ',
        password2='killerqueen')
    assert_equal(form.fullname.data, 'Freddy Mercury')
    assert_equal(form.username.data, 'fred@queen.com')
    assert_equal(form.username2.data, 'fred@queen.com')
    assert_equal(form.password.data, 'killerqueen')
    assert_equal(form.password2.data, 'killerqueen')


def test_merge_account_form_cleaning():
    form = MergeAccountForm(merged_username='freD@queen.com\t ',
        merged_password='rhapsodY123 ',
        user_password='bohemi1aN ')
    assert_equal(form.merged_username.data, 'fred@queen.com')
    assert_equal(form.merged_password.data, 'rhapsodY123')
    assert_equal(form.user_password.data, 'bohemi1aN')


# TODO: test validation
