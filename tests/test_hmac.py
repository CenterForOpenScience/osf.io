# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts

from website import hmac


def test_signing_and_loading():
    signed = hmac.sign('killerqueen')
    assert_equal(hmac.load(signed), 'killerqueen')
