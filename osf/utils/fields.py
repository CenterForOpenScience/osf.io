import jwe
from django.db import models
from website import settings

from osf.exceptions import NaiveDatetimeException

SENSITIVE_DATA_KEY = jwe.kdf(settings.SENSITIVE_DATA_SECRET.encode('utf-8'),
                             settings.SENSITIVE_DATA_SALT.encode('utf-8'))

def ensure_bytes(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, bytes):
        return value
    return value.encode('utf-8')

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

    def get_db_prep_value(self, value, **kwargs):
        if value and not value.startswith(self.prefix):
            value = ensure_bytes(value)
            if not settings.RUNNING_MIGRATION:
                # don't encrypt things if we're migrating.
                value = self.prefix + jwe.encrypt(bytes(value), SENSITIVE_DATA_KEY)
            else:
                # just prefix them
                return u'jwe:::{}'.format(value)
        return value

    def to_python(self, value):
        if value and value.startswith(self.prefix):
            value = ensure_bytes(value)
            if not settings.RUNNING_MIGRATION:
                # don't decrypt things if we're migrating.
                value = jwe.decrypt(bytes(value[len(self.prefix):]), SENSITIVE_DATA_KEY)
            else:
                return value[6:]
        return value

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)


class NonNaiveDateTimeField(models.DateTimeField):
    def get_prep_value(self, value):
        value = super(NonNaiveDateTimeField, self).get_prep_value(value)
        if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
            raise NaiveDatetimeException('Tried to encode a naive datetime.')
        return value
