from django.db import models
from django.db.models import JSONField

from website import settings
from osf.utils import functional, cryptography
from osf.exceptions import NaiveDatetimeException


def ensure_bytes(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, bytes):
        return value
    elif isinstance(value, str):
        return value.encode()
    else:
        raise NotImplementedError(f'datatype [{type(value)}] not implemented')


def ensure_str(value):
    """Helper function to ensure all inputs are encoded to the proper value utf-8 value regardless of input type"""
    if isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode()
    else:
        raise NotImplementedError(f'datatype [{type(value)}] not implemented')


def encrypt_string(value, prefix=b'jwe:::'):
    if value:
        return (prefix + cryptography.encrypt(ensure_bytes(value), SENSITIVE_DATA_KEY).encode()).decode()


def decrypt_string(value, prefix=b'jwe:::'):
    if value:
        return cryptography.decrypt(ensure_bytes(value), SENSITIVE_DATA_KEY)


class LowercaseCharField(models.CharField):
    def get_prep_value(self, value):
        value = super(models.CharField, self).get_prep_value(value)
        if value is not None:
            value = value.lower()
        return value


class LowercaseEmailField(models.EmailField):
    # Note: This is technically not compliant with RFC 822, which requires
    #       that case be preserved in the "local-part" of an address. From
    #       a practical standpoint, the vast majority of email servers do
    #       not preserve case.
    #       ref: https://tools.ietf.org/html/rfc822#section-6
    def get_prep_value(self, value):
        value = super(models.EmailField, self).get_prep_value(value)
        if value is not None:
            value = value.lower().strip()
        return value


class EncryptedTextField(models.TextField):
    """
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    """
    prefix = b'jwe:::'

    def get_db_prep_value(self, value, **kwargs):
        return encrypt_string(value, prefix=self.prefix)

    def to_python(self, value):
        print(self, value)
        if value:
            return decrypt_string(value, prefix=self.prefix)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)


class NonNaiveDateTimeField(models.DateTimeField):
    def get_prep_value(self, value):
        value = super(NonNaiveDateTimeField, self).get_prep_value(value)
        if value is not None and (value.tzinfo is None or value.tzinfo.utcoffset(value) is None):
            raise NaiveDatetimeException('Tried to encode a naive datetime.')
        return value


class EncryptedJSONField(JSONField):
    """
    Very similar to EncryptedTextField, but for postgresql's JSONField
    """
    prefix = b'jwe:::'

    def get_prep_value(self, value, **kwargs):
        if value:
            value = functional.rapply(value, encrypt_string, prefix=self.prefix)

        return super().get_prep_value(value, **kwargs)

    def to_python(self, value):
        return functional.rapply(value, decrypt_string, prefix=self.prefix)

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        return self.to_python(value)


SENSITIVE_DATA_KEY = cryptography.kdf(
    ensure_bytes(settings.SENSITIVE_DATA_SECRET),
    ensure_bytes(settings.SENSITIVE_DATA_SALT)
)
