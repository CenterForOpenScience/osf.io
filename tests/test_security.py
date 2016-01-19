# -*- coding: utf-8 -*-
from nose.tools import *

from tests.base import OsfTestCase
from website import security
from test_features import requires_gnupg

class TestSecurityFunctions(OsfTestCase):
    def test_random_string(self):
        s = security.random_string(length=30)
        assert_true(isinstance(s, basestring))
        assert_equal(len(s), 30)
        s2 = security.random_string(30)
        assert_not_equal(s, s2)  # This will fail with some non zero probability

    def test_random_pin(self):
        # test default
        s = security.random_pin()
        assert_true(isinstance(s,int))
        assert_equal(len(str(s)),6)

        # test a custom length
        s_2 = security.random_pin(100)
        assert_equal(len(str(s_2)),100)

        # test random bounds
        for i in range(100):
            s_default = security.random_pin()
            assert_true(s_default >=10**(6-1))
            assert_true(s_default < 10**6-1)

        random_one_digit_pins = []
        # test the "1" parameter
        for i in range(100):
            s_one = security.random_pin(1)
            random_one_digit_pins.append(s_one)
            assert_true(s_one >=0)
            assert_true(s_one < 10)

        # test failure on bad parameterss
        with self.assertRaises(ValueError):
            security.random_pin(0)

        with self.assertRaises(ValueError):
            security.random_pin(-10)


    @requires_gnupg
    def test_encryption(self):
        encryption = security.Encryption()
        private_string = 'p4ssw0rd'

        # Encrypted string is obfuscated
        encrypted_string = encryption.encrypt(private_string)
        assert_not_in(private_string, encrypted_string)

        # Original string can be recovered
        decrypted_string = encryption.decrypt(encrypted_string)
        assert_equal(decrypted_string, private_string)
