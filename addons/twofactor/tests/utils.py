import time
from base64 import b32encode

from pyotp import TOTP


def _valid_code(seed, drift=0):
    """Generate a valid code.

    :param drift: Number of periods to drift from current time. Optional.
    :return: valid 6-character two-factor response
    :rtype: str
    """
    client = TOTP(b32encode(seed.encode()).decode())
    return client.at(int(time.time()) + (drift * 30))
