# -*- coding: utf-8 -*-
from nose.tools import *

from website import security


def test_random_string():
    s = security.random_string(length=30)
    assert_true(isinstance(s, basestring))
    assert_equal(len(s), 30)
    s2 = security.random_string(30)
    assert_not_equal(s, s2)
