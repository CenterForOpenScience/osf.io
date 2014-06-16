# -*- coding: utf-8 -*-
"""Security utilities."""
# TODO: put in website/utils/ when rubeus circular import issue is resolved
import string
import gnupg
import logging
from random import SystemRandom

from website import settings

random = SystemRandom()

logging.getLogger('gnupg').setLevel(logging.WARNING)


def random_string(length=8, chars=string.letters+string.digits):
    """Generate a random string of a given length.
    """
    return ''.join([chars[random.randint(0, len(chars)-1)] for i in range(length)])


class Encryption(object):

    gpg = gnupg.GPG(gnupghome=settings.GNUPGHOME)
    keys = gpg.list_keys()

    if not keys:
        raise RuntimeError(
            "No GnuPG key found. Did you remember to 'invoke encryption'?"
        )

    fingerprint = keys[0]['fingerprint']

    def encrypt(self, value):
        return str(self.gpg.encrypt(value, self.fingerprint, always_trust=True))

    def decrypt(self, encrypted_data):
        return str(self.gpg.decrypt(encrypted_data, always_trust=True))


encryptor = Encryption()

encrypt = encryptor.encrypt
decrypt = encryptor.decrypt