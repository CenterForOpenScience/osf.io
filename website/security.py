# -*- coding: utf-8 -*-
"""Security utilities."""
# TODO: put in website/utils/ when rubeus circular import issue is resolved
import string
import gnupg
from random import SystemRandom

from website.settings import FINGERPRINT, PRIVATE_KEY

random = SystemRandom()


def random_string(length=8, chars=string.letters+string.digits):
    """Generate a random string of a given length.
    """
    return ''.join([chars[random.randint(0, len(chars)-1)] for i in range(length)])


class Encryption(object):

    gpg = gnupg.GPG()

    if FINGERPRINT not in gpg.list_keys()[0].values():
        gpg.import_keys(PRIVATE_KEY)

    def encrypt(self, value):
        return str(self.gpg.encrypt(value, FINGERPRINT, always_trust=True))

    def decrypt(self, encrypted_data):
        return str(self.gpg.decrypt(encrypted_data, always_trust=True))