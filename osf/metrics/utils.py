import re
import datetime
import typing
from hashlib import sha256

from elasticsearch_dsl import analyzer, tokenizer


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
    year: int   # assumed >= 1000, < 10000
    month: int  # assumed >= 1, <= 12

    YEARMONTH_RE = re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})')

    @classmethod
    def from_date(cls, date):
        assert isinstance(date, (datetime.datetime, datetime.date))
        return cls(date.year, date.month)

    @classmethod
    def from_str(cls, input_str):
        match = cls.YEARMONTH_RE.fullmatch(input_str)
        if match:
            return cls(
                year=int(match.group('year')),
                month=int(match.group('month')),
            )
        else:
            raise ValueError(f'expected YYYY-MM format, got "{input_str}"')

    def __str__(self):
        return f'{self.year}-{self.month:0>2}'

    def as_datetime(self) -> datetime.datetime:
        return datetime.datetime(self.year, self.month, 1, tzinfo=datetime.timezone.utc)

    def next(self):
        if self.month == 12:
            return YearMonth(self.year + 1, 1)
        return YearMonth(self.year, self.month + 1)

    def prior(self):
        if self.month == 1:
            return YearMonth(self.year - 1, 12)
        return YearMonth(self.year, self.month - 1)


# for elasticsearch fields that hold dot-delimited paths,
# to allow querying/aggregating by prefix (e.g. 'root.to.leaf'
# yields tokens ['root', 'root.to', 'root.to.leaf'])
route_prefix_tokenizer = tokenizer('route_prefix_tokenizer', 'path_hierarchy', delimiter='.')
route_prefix_analyzer = analyzer('route_prefix_analyzer', tokenizer=route_prefix_tokenizer)
