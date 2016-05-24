from __future__ import absolute_import, unicode_literals

from Crypto.Cipher import AES
import hashlib

from admin.base.settings import DESK_KEY, DESK_ITERATIONS

AES_MULTIPLE = 16


def generate_key(key=DESK_KEY, iterations=DESK_ITERATIONS):
    for i in range(iterations):
        key = hashlib.sha256(key).digest()
    return key


def pad_text(text, multiple=AES_MULTIPLE):
    padding_size = multiple - (len(text) % multiple)
    padding = chr(padding_size) * padding_size
    return text + padding


def unpad_text(padded_text):
    padding_size = ord(padded_text[-1])
    return padded_text[:-padding_size]


def encrypt(plaintext):
    key = generate_key()
    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = pad_text(plaintext)
    return cipher.encrypt(padded_plaintext).__repr__().decode('utf8')


def decrypt(ciphertext, key=DESK_KEY):
    key = generate_key(key=key)
    cipher = AES.new(key, AES.MODE_ECB)
    padded_plaintext = cipher.decrypt(eval(ciphertext.encode('utf8')))
    return unpad_text(padded_plaintext)


