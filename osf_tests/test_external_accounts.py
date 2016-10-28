import string
import random

import jwe
import pytest
from django.db import connection
from psycopg2._psycopg import AsIs

from osf.models import ExternalAccount
from osf.utils.fields import EncryptedTextField, SENSITIVE_DATA_KEY
from .factories import ExternalAccountFactory

@pytest.mark.django_db
class TestEncryptedStringField(object):
    def setup_class(self):
        self.magic_string = ''.join(random.choice(string.hexdigits) for _ in range(25))

        self.encrypted_field_dict = {f.name: self.magic_string for f in
                                ExternalAccountFactory._meta.model._meta.get_fields() if
                                isinstance(f, EncryptedTextField)}

    def test_values_match(self):
        eaf = ExternalAccountFactory(**self.encrypted_field_dict)
        ea = ExternalAccount.objects.get(id=eaf.id)
        ea.reload()

        for field_name, value in self.encrypted_field_dict.iteritems():
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
