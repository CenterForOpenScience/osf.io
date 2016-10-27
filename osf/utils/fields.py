import jwe
from django.db import models
from website import settings


class LowercaseCharField(models.CharField):
    def get_prep_value(self, value):
        value = super(models.CharField, self).get_prep_value(value)
        if value is not None:
            value = value.lower()
        return value


class EncryptedStringField(models.CharField):
    prefix = 'jwe:::'
    SENSITIVE_DATA_KEY = jwe.kdf(settings.SENSITIVE_DATA_SECRET.encode('utf-8'), settings.SENSITIVE_DATA_SALT.encode('utf-8'))

    def get_db_prep_value(self, value, **kwargs):
        if not value or not value.startswith(self.prefix):
            return value
        return self.prefix + jwe.encrypt(bytes(value), self.SENSITIVE_DATA_KEY)

    def to_python(self, value):
        if not value or not value.startswith(self.prefix):
            return value
        return jwe.decrypt(bytes(value[len(self.prefix):]), self.SENSITIVE_DATA_KEY)
