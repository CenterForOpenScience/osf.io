# -*- coding: utf-8 -*-
from nose.tools import *

from framework.encryption import encrypt, decrypt
from website import security


def test_random_string():
    s = security.random_string(length=30)
    assert_true(isinstance(s, str))
    assert_equal(len(s), 30)
    s2 = security.random_string(30)
    assert_not_equal(s, s2)


def test_encryption():
    private_string = 'p4ssw0rd'

    # Encrypted string is obfuscated
    encrypted_string = encrypt(private_string)
    assert_not_in(private_string, encrypted_string)

    # Original string can be recovered
    decrypted_string = decrypt(encrypted_string)
    assert_equal(decrypted_string, private_string)
