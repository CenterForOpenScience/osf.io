# -*- coding: utf-8 -*-

import unittest
from nose.tools import *  # noqa

from framework.encryption import encrypt, decrypt, ensure_str

class EncryptionTestCase(unittest.TestCase):

    def test_ensure_str_encodes_no_unicode_in_string_type_str(self):
        my_value = 'hello'
        my_str = ensure_str(my_value)
        assert_true(isinstance(my_str, str))

    def test_ensure_str_encodes_unicode_in_string_type_str(self):
        my_value = 'hellü'
        my_str = ensure_str(my_value)
        assert_true(isinstance(my_str, str))

    def test_ensure_str_encodes_no_unicode_in_string_type_unicode(self):
        my_value = u'hello'
        my_str = ensure_str(my_value)
        assert_true(isinstance(my_str, str))

    def test_ensure_str_encodes_unicode_in_string_type_unicode(self):
        my_value = u'hellü'
        my_str = ensure_str(my_value)
        assert_true(isinstance(my_str, str))

    def test_encrypt_and_decrypt_no_unicode_in_string_type_str(self):
        my_value = 'hello'
        my_value_encrypted = encrypt(my_value)
        assert_true(isinstance(my_value_encrypted, str))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert_true(isinstance(my_value_decrypted, str))
        assert_equal(my_value_decrypted, ensure_str(my_value))

    def test_encrypt_and_decrypt_unicode_in_string_type_str(self):
        my_value = 'hellü'
        my_value_encrypted = encrypt(my_value)
        assert_true(isinstance(my_value_encrypted, str))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert_equal(my_value_decrypted, ensure_str(my_value))

        my_value = '찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        my_value_encrypted = encrypt(my_value)
        my_value_decrypted = decrypt(my_value_encrypted)
        assert_true(isinstance(my_value_decrypted, str))
        assert_equal(my_value_decrypted, ensure_str(my_value))

    def test_encrypt_and_decrypt_no_unicode_in_string_type_unicode(self):
        my_value = u'hello'
        my_value_encrypted = encrypt(my_value)
        assert_true(isinstance(my_value_encrypted, str))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert_true(isinstance(my_value_decrypted, str))
        assert_equal(my_value_decrypted, ensure_str(my_value))

    def test_encrypt_and_decrypt_unicode_in_string_type_unicode(self):
        my_value = u'hellü'
        my_value_encrypted = encrypt(my_value)
        assert_true(isinstance(my_value_encrypted, str))

        my_value_decrypted = decrypt(my_value_encrypted)
        assert_equal(my_value_decrypted, ensure_str(my_value))

        my_value = u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        my_value_encrypted = encrypt(my_value)
        my_value_decrypted = decrypt(my_value_encrypted)
        assert_true(isinstance(my_value_decrypted, str))
        assert_equal(my_value_decrypted, ensure_str(my_value))
