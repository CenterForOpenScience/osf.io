import time

from oath import totp


def _valid_code(seed, drift=0):
        """Generate a valid code.

        :param drift: Number of periods to drift from current time. Optional.
        :return: valid 6-character two-factor response
        :rtype: str
        """
        return totp(
            key=seed,
            t=int(time.time()) + (drift * 30)
        )