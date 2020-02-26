# -*- coding: utf-8 -*-
"""Security utilities."""
# TODO: put in website/utils/ when rubeus circular import issue is resolved
import string
from random import SystemRandom

random = SystemRandom()


def random_string(length=8, chars=string.ascii_letters + string.digits):
    """Generate a random string of a given length.
    """
    return ''.join([chars[random.randint(0, len(chars) - 1)] for i in range(length)])
