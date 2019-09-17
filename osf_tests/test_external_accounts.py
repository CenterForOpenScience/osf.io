# -*- coding: utf-8 -*-
import string
import random

import jwe
import pytest
from django.db import connection
from psycopg2._psycopg import AsIs

from osf.models import ExternalAccount
from osf.utils.fields import EncryptedTextField, SENSITIVE_DATA_KEY, ensure_bytes
from .factories import ExternalAccountFactory

@pytest.mark.django_db
class TestEncryptedExternalAccountFields(object):
    def setup_class(self):
        self.magic_string = ''.join(random.choice(string.hexdigits) for _ in range(25))

        self.encrypted_field_dict = {f.name: self.magic_string for f in
                                ExternalAccountFactory._meta.model._meta.get_fields() if
                                isinstance(f, EncryptedTextField)}

    def test_values_match(self):
        eaf = ExternalAccountFactory(**self.encrypted_field_dict)
        ea = ExternalAccount.objects.get(id=eaf.id)
        ea.reload()

        for field_name, value in self.encrypted_field_dict.items():
                assert self.encrypted_field_dict[field_name] == getattr(ea, field_name)

    def test_database_is_encrypted(self):
        eaf = ExternalAccountFactory(**self.encrypted_field_dict)
        ea = ExternalAccount.objects.get(id=eaf.id)
        ea.reload()
        sql = """
            SELECT %s FROM osf_externalaccount WHERE id = %s;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [AsIs(', '.join(self.encrypted_field_dict.keys())), ea.id])
            row = cursor.fetchone()
            for blicky in row:
                assert jwe.decrypt(bytes(blicky[len(EncryptedTextField.prefix):]), SENSITIVE_DATA_KEY) == self.magic_string


class TestEncryptedTextField:
    @pytest.fixture
    def field(self):
        return EncryptedTextField(null=True, blank=True)

    def test_ensure_bytes_encodes_no_unicode_in_string_type_str(self):
        my_value = 'hello'
        assert isinstance(my_value, bytes)
        my_str = ensure_bytes(my_value)
        assert isinstance(my_str, bytes)

    def test_ensure_bytes_encodes_unicode_in_string_type_str(self):
        my_value = 'hellü'
        assert isinstance(my_value, bytes)
        my_str = ensure_bytes(my_value)
        assert isinstance(my_str, bytes)

    def test_ensure_bytes_encodes_no_unicode_in_string_type_unicode(self):
        my_value = u'hello'
        assert isinstance(my_value, str)
        my_str = ensure_bytes(my_value)
        assert isinstance(my_str, bytes)

    def test_ensure_bytes_encodes_unicode_in_string_type_unicode(self):
        my_value = u'hellü'
        assert isinstance(my_value, str)
        my_str = ensure_bytes(my_value)
        assert isinstance(my_str, bytes)

    def test_encrypt_and_decrypt_no_unicode_in_string_type_str(self, field):
        my_value = 'hello'
        assert isinstance(my_value, bytes)
        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, bytes)
        assert my_value_decrypted == ensure_bytes(my_value)

    def test_encrypt_and_decrypt_unicode_in_string_type_str(self, field):
        my_value = 'hellü'
        assert isinstance(my_value, bytes)
        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert my_value_decrypted == ensure_bytes(my_value)

        my_value = '찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        assert isinstance(my_value, bytes)
        my_value_encrypted = field.get_db_prep_value(my_value)
        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, bytes)
        assert my_value_decrypted == ensure_bytes(my_value)

    def test_encrypt_and_decrypt_no_unicode_in_string_type_unicode(self, field):
        my_value = u'hello'
        assert isinstance(my_value, str)
        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, bytes)
        assert my_value_decrypted == ensure_bytes(my_value)

    def test_encrypt_and_decrypt_unicode_in_string_type_unicode(self, field):
        my_value = u'hellü'
        assert isinstance(my_value, str)
        my_value_encrypted = field.get_db_prep_value(my_value)
        assert isinstance(my_value_encrypted, bytes)

        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert my_value_decrypted == ensure_bytes(my_value)

        my_value = u'찦차КЛМНО💁◕‿◕｡)╱i̲̬͇̪͙n̝̗͕v̟̜̘̦͟o̶̙̰̠kè͚̮̺̪̹̱̤  ǝɹol'
        assert isinstance(my_value, str)
        my_value_encrypted = field.get_db_prep_value(my_value)
        my_value_decrypted = field.from_db_value(my_value_encrypted, None, None, None)
        assert isinstance(my_value_decrypted, bytes)
        assert my_value_decrypted == ensure_bytes(my_value)
