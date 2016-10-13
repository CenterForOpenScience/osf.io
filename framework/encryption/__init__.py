import jwe

from modularodm.fields import StringField

from website import settings

SENSITIVE_DATA_KEY = jwe.kdf(settings.SENSITIVE_DATA_SECRET.encode('utf-8'), settings.SENSITIVE_DATA_SALT.encode('utf-8'))

def encrypt(value):
    if value:
        return jwe.encrypt(value.encode('utf-8'), SENSITIVE_DATA_KEY)
    return None

def decrypt(value):
    if value:
        return jwe.decrypt(value.encode('utf-8'), SENSITIVE_DATA_KEY)
    return None

class EncryptedStringField(StringField):

    def to_storage(self, value, translator=None):
        value = encrypt(value)
        return super(EncryptedStringField, self).to_storage(value, translator=translator)

    def from_storage(self, value, translator=None):
        value = super(EncryptedStringField, self).from_storage(value, translator=translator)
        return decrypt(value)
