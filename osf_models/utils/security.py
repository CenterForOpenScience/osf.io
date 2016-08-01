# -*- coding: utf-8 -*-
"""Security utilities."""
##### copied from website.security #####
import string
import logging
from random import SystemRandom

from website import settings

random = SystemRandom()

def random_string(length=8, chars=string.letters + string.digits):
    """Generate a random string of a given length.
    """
    return ''.join([chars[random.randint(0, len(chars) - 1)] for i in range(length)])
