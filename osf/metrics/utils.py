from __future__ import annotations
import calendar
import dataclasses
import re
import datetime
from hashlib import sha256
from typing import ClassVar


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


@dataclasses.dataclass(frozen=True)
class YearMonth:
    """YearMonth: represents a specific month in a specific year"""
    year: int
    month: int

    YEARMONTH_RE: ClassVar[re.Pattern] = re.compile(r'(?P<year>\d{4})-(?P<month>\d{2})')

    @classmethod
    def from_date(cls, date: datetime.date) -> YearMonth:
        """construct a YearMonth from a `datetime.date` (or `datetime.datetime`)"""
        return cls(date.year, date.month)

    @classmethod
    def from_str(cls, input_str: str) -> YearMonth:
        """construct a YearMonth from a string in "YYYY-MM" format"""
        match = cls.YEARMONTH_RE.fullmatch(input_str)
        if match:
            return cls(
                year=int(match.group('year')),
                month=int(match.group('month')),
            )
        else:
            raise ValueError(f'expected YYYY-MM format, got "{input_str}"')

    @classmethod
    def from_any(cls, data) -> YearMonth:
        if isinstance(data, YearMonth):
            return data
        elif isinstance(data, str):
            return YearMonth.from_str(data)
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return YearMonth.from_date(data)
        raise ValueError(f'cannot coerce {data} into YearMonth')

    def __str__(self):
        """convert to string of "YYYY-MM" format"""
        return f'{self.year}-{self.month:0>2}'

    def next(self) -> YearMonth:
        """get a new YearMonth for the month after this one"""
        return (
            YearMonth(self.year + 1, int(calendar.JANUARY))
            if self.month == calendar.DECEMBER
            else YearMonth(self.year, self.month + 1)
        )

    def prior(self) -> YearMonth:
        """get a new YearMonth for the month before this one"""
        return (
            YearMonth(self.year - 1, int(calendar.DECEMBER))
            if self.month == calendar.JANUARY
            else YearMonth(self.year, self.month - 1)
        )

    def month_start(self) -> datetime.datetime:
        """get a datetime (in UTC timezone) when this YearMonth starts"""
        return datetime.datetime(self.year, self.month, 1, tzinfo=datetime.UTC)

    def month_end(self) -> datetime.datetime:
        """get a datetime (in UTC timezone) when this YearMonth ends (the start of next month)"""
        return self.next().month_start()
