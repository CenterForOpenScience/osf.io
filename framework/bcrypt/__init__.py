# Adapted from:
#   Name: Flask-Bcrypt
#   Version: 0.3.2
#   Summary: Bcrypt support for hashing passwords
#   Home-page: https://github.com/maxcountryman/flask-bcrypt
#   Author: Max Countryman
#   Author-email: maxc@me.com
#   License: BSD

import bcrypt
from website import settings

def generate_password_hash(password, rounds=None):
    '''Generates a password hash using `bcrypt`. Specifying `log_rounds` sets
    the log_rounds parameter of `bcrypt.gensalt()` which determines the
    complexity of the salt. 12 is the default value.

    Returns the hashed password.
    '''

    if rounds is None:
        rounds = settings.BCRYPT_LOG_ROUNDS

    if not password:
        raise ValueError('Password must be non-empty.')

    pw_hash = bcrypt.hashpw(
        str(password).encode('utf-8'),
        bcrypt.gensalt(rounds)
    )

    return pw_hash


def constant_time_compare(val1, val2):
    '''Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.
    '''

    if len(val1) != len(val2):
        return False

    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)

    return result == 0


def check_password_hash(pw_hash, password):
    '''Checks a hashed password against a password.

    Returns `True` if the password matched, `False` otherwise.
    '''

    return constant_time_compare(
        bcrypt.hashpw(
            str(password).encode('utf-8'),
            str(pw_hash).encode('utf-8')
        ),
        pw_hash
    )
