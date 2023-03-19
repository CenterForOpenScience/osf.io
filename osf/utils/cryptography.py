import os
import json
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import (
    modes,
    Cipher,
    algorithms
)

backend = default_backend()


def base64_urlsafe_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')


def base64_urlsafe_decode(data):
    return base64.urlsafe_b64decode(data + (b'=' * (len(data) % 4)))


def kdf(key, salt, length=32, iterations=10000):
    return PBKDF2HMAC(
        salt=salt,
        length=length,
        backend=backend,
        iterations=iterations,
        algorithm=hashes.SHA256(),
    ).derive(key)


def encrypt(data, key):
    segments = []

    header = {
        'alg': 'dir',
        'enc': 'A256GCM'
    }
    segments.append(
        base64_urlsafe_encode(
            json.dumps(header).encode()
        )
    )

    segments.append(b'')  # Keywrapping is for suckers

    iv = os.urandom(16)
    segments.append(
        base64_urlsafe_encode(iv)
    )

    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=backend,
    ).encryptor()

    encryptor.authenticate_additional_data(segments[0])
    ciphertext = encryptor.update(data) + encryptor.finalize()
    segments.append(base64_urlsafe_encode(ciphertext))

    segments.append(base64_urlsafe_encode(encryptor.tag))
    return b'.'.join(segments).decode()


def decrypt(data, key):
    spl = data.split(b'.')

    try:
        header, encrypted_key, iv, ciphertext, tag = [x for x in spl]
    except ValueError:
        raise MalformedData(f'Recieved incorrected formatted data. Expected 5 segments, received {len(spl)}')

    if encrypted_key:
        raise UnsupportedOption('Key wrapping is currently not supported')

    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag),
        backend=backend,
    ).decryptor()

    encryptor.authenticate_additional_data(spl[0])

    return encryptor.update(ciphertext) + encryptor.finalize()


class PyJWEException(Exception):
    pass


class MalformedData(PyJWEException):
    pass


class UnsupportedOption(PyJWEException):
    pass
