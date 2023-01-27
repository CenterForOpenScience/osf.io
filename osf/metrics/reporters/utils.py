import pytz
import datetime
import typing
from hashlib import sha256


def stable_key(*key_parts):
    """hash function for use in osf.metrics

    positional args: non-None, str-able things to hash
    """
    if not key_parts:
        raise ValueError('stable_key requires args')
    if any((val is None) for val in key_parts):
        raise ValueError('all key_parts must be non-None')

    plain_key = '|'.join(map(str, key_parts))
    return sha256(bytes(plain_key, encoding='utf')).hexdigest()


class YearMonth(typing.NamedTuple):
    year: int
    month: int

    def __str__(self):
        return f'{self.year}-{self.month}'

    def target_month(self):
        return datetime.datetime(self.year, self.month, 1, tzinfo=pytz.utc)

    def next_month(self):
        if self.month == 12:
            return datetime.datetime(self.year + 1, 1, 1, tzinfo=pytz.utc)
        return datetime.datetime(self.year, self.month + 1, 1, tzinfo=pytz.utc)
