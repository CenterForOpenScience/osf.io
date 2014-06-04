# -*- coding: utf-8 -*-
"""Security utilities."""
# TODO: put in website/utils/ when rubeus circular import issue is resolved
import string
import gnupg
from random import SystemRandom

from website import settings

random = SystemRandom()


def random_string(length=8, chars=string.letters+string.digits):
    """Generate a random string of a given length.
    """
    return ''.join([chars[random.randint(0, len(chars)-1)] for i in range(length)])


class Encryption(object):

    gpg = gnupg.GPG(gnupghome=settings.GNUPGHOME)

    if not gpg.list_keys() or settings.FINGERPRINT not in gpg.list_keys()[0].values():
        raise ImportError(
            "No GnuPG keyring found. Did you remember to 'invoke encryption'?"
        )

    def encrypt(self, value):
        return str(self.gpg.encrypt(value, settings.FINGERPRINT, always_trust=True))

    def decrypt(self, encrypted_data):
        return str(self.gpg.decrypt(encrypted_data, always_trust=True))
