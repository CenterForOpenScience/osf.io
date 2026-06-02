from __future__ import annotations
import calendar
import dataclasses
import re
import datetime
from hashlib import sha256
from typing import ClassVar

from elasticsearch_metrics.util.timeparts import serialize_timeparts

from osf.metadata.osfmap_utils import (
    osfmap_type,
    osfmap_type_from_model,
)
from website import settings as website_settings


def cycle_coverage_date(given_date: datetime.date) -> str:
    """
    >>> cycle_coverage_date(datetime.date(1234, 5, 6))
    '1234.5.6'
    >>> cycle_coverage_date(datetime.datetime(7654, 3, 2, 1))
    '7654.3.2'
    """
    return serialize_timeparts((given_date.year, given_date.month, given_date.day), 3)


def cycle_coverage_yearmonth(given_ym: YearMonth | datetime.date) -> str:
    """
    >>> cycle_coverage_yearmonth(YearMonth(2222, 33))
    '2222.33'
    >>> cycle_coverage_yearmonth(datetime.date(1234, 5, 6))
    '1234.5'
    """
    return serialize_timeparts((given_ym.year, given_ym.month), 2)


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


def get_database_iri(osf_obj) -> str:
    _provider = getattr(osf_obj, 'provider', None)
    if not _provider:
        return website_settings.DOMAIN
    elif isinstance(_provider, str):
        # file providers are a different thing that don't really have an iri, just an id
        return f'urn:files.osf.io:{_provider}'
    else:
        return _provider.get_semantic_iri()


def get_item_type(osf_obj) -> str:
    return get_item_type_from_iri(osfmap_type(osf_obj))


def get_item_type_from_model(osf_model_cls, *, is_component: bool) -> str:
    return get_item_type_from_iri(
        osfmap_type_from_model(osf_model_cls, is_component=is_component),
    )


def get_item_type_from_iri(type_iri) -> str:
    (_, _, _shortname) = type_iri.rpartition('/')
    return _shortname


def get_surrounding_osfids(osfid_referent):
    """get all the parent/owner/surrounding osfids for the given osfid_referent

    @param osfid_referent: instance of a model that has GuidMixin
    @returns list of str

    For AbstractNode, goes up the node hierarchy up to the root.
    For WikiPage or BaseFileNode, grab the node it belongs to and
    follow the node hierarchy from there.
    """
    _surrounding_osfids = []
    _current_referent = osfid_referent
    while _current_referent:
        next_referent = get_immediate_wrapper(_current_referent)
        if next_referent:
            _surrounding_osfids.append(next_referent._id)
        _current_referent = next_referent
    return _surrounding_osfids


def get_immediate_wrapper(osfid_referent):
    if hasattr(osfid_referent, 'verified_publishable'):
        return None                                     # quacks like Preprint
    return (
        getattr(osfid_referent, 'parent_node', None)     # quacks like AbstractNode
        or getattr(osfid_referent, 'node', None)         # quacks like WikiPage, Comment
        or getattr(osfid_referent, 'target', None)       # quacks like BaseFileNode
    )


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
    def from_today(cls) -> YearMonth:
        """construct a YearMonth from the current moment"""
        return cls.from_date(datetime.date.today())

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
