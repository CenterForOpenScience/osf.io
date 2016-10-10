import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import modes
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from modularodm.fields import StringField

from website.settings import SENSITIVE_DATA_JWE_KEY

backend = default_backend()

def encrypt(data):
    if data:
        key = SENSITIVE_DATA_JWE_KEY
        segments = []

        iv = os.urandom(16)
        segments.append(base64.b64encode(iv))

        encryptor = Cipher(algorithms.AES(key), modes.GCM(iv), backend=backend).encryptor()
        ciphertext = encryptor.update(data.encode('utf-8')) + encryptor.finalize()
        segments.append(base64.b64encode(ciphertext))

        segments.append(base64.b64encode(encryptor.tag))

        return b'.'.join(segments)
    return None

def decrypt(data):
    if data:
        key = SENSITIVE_DATA_JWE_KEY
        spl = data.split(b'.')

        try:
            iv, ciphertext, tag = [base64.b64decode(x) for x in spl]
        except ValueError:
            raise Exception('Recieved incorrected formatted data. Expected 3 segments, received {}'.format(len(spl)))

        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=backend
        ).decryptor()

        return encryptor.update(ciphertext) + encryptor.finalize()
    return None


class EncryptedStringField(StringField):

    def to_storage(self, value, translator=None):
        value = encrypt(value)
        return super(EncryptedStringField, self).to_storage(value, translator=translator)

    def from_storage(self, value, translator=None):
        value = super(EncryptedStringField, self).from_storage(value, translator=translator)
        return decrypt(value)
