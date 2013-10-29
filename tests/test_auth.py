#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
from tests.base import DbTestCase

import framework.auth as auth
from framework.auth.model import User



class TestAuth(DbTestCase):

    def setUp(self):
        pass

    def test_register(self):
        auth.register('rosie@franklin.com', 'gattaca', fullname="Rosie Franklin")
        assert_equal(User.find().count(), 1)
        user = User.find()[0]
        # The password should be set
        assert_true(user.check_password('gattaca'))
        assert_equal(user.fullname, "Rosie Franklin")
        assert_equal(user.username, 'rosie@franklin.com')
        assert_in("rosie@franklin.com", user.emails)


if __name__ == '__main__':
    unittest.main()
