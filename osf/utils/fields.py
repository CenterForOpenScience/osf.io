import jwe
from django.db import models
from website import settings


class LowercaseCharField(models.CharField):
    def get_prep_value(self, value):
        value = super(models.CharField, self).get_prep_value(value)
        if value is not None:
            value = value.lower()
        return value


class EncryptedTextField(models.TextField):
    '''
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    '''
    prefix = 'jwe:::'
    SENSITIVE_DATA_KEY = jwe.kdf(settings.SENSITIVE_DATA_SECRET.encode('utf-8'), settings.SENSITIVE_DATA_SALT.encode('utf-8'))

    def get_db_prep_value(self, value, **kwargs):
        if value and not value.startswith(self.prefix):
            value = self.prefix + jwe.encrypt(bytes(value), self.SENSITIVE_DATA_KEY)
        return value

    def to_python(self, value):
        if value and value.startswith(self.prefix):
            value = jwe.decrypt(bytes(value[len(self.prefix):]), self.SENSITIVE_DATA_KEY)
        return value

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)
