from __future__ import unicode_literals

import re
from functools import partial

import requests

from dateutil import parser

from website.addons.app.exceptions import SchemaViolationError


DOI_HEADERS = {'Accept': 'application/json'}
DOI_KEYS = [
    'issue',
    'publisher',
    'DOI',
    'subtitle',
    'score',
    'author',
    'URL',
    'issued',
    'reference-count',
    'ISSN',
    'volume',
    'source',
    'prefix',
    'member',
    'deposited',
    'container-title',
    'indexed',
    'title',
    'type',
    'page',
    'subject'
]


def _must_be_type(_type, key, value):
    if not isinstance(value, _type):
        raise SchemaViolationError('{} must be of type {}'.format(key, _type))
    return value


def _regex(rgx, key, value):
    if isinstance(value, basestring) and re.compile(rgx).search(value):
        return value
    raise SchemaViolationError('{} must follow the pattern {}'.format(key, rgx))


def regex(pattern):
    ret = partial(_regex, pattern)
    ret.__doc__ = '<Regex Pattern {}>'.format(pattern)
    return ret


def must_be_type(_type):
    ret = partial(_must_be_type, _type)
    ret.__doc__ = str(_type)
    return ret


def orcid(key, orcid):
    '''TODO Write a doc string'''
    try:
        ret = requests.get('https://pub.orcid.org/{}'.format(orcid), headers=DOI_HEADERS)
    except Exception:
        raise SchemaViolationError('{} is not a valid ORCID'.format(key))

    if ret.status_code != 200:
        raise SchemaViolationError('{} is not a valid ORCID'.format(key))
    return ret.json()

def doi(key, doi):
    '''TODO Write a doc string'''
    if isinstance(doi, dict):
        if DOI_KEYS == doi.keys():
            return doi
    try:
        ret = requests.get(doi, headers=DOI_HEADERS)
    except Exception:
        raise SchemaViolationError('{} at key {} is not a valid doi'.format(doi, key))

    if ret.status_code != 200:
        raise SchemaViolationError('{} at key {} is not a valid doi'.format(doi, key))
    return ret.json()


def must_be_date(key, value):
    '''<type 'datetime.datetime'>'''
    try:
        return parser.parse(value).isoformat()
    except TypeError:
        raise SchemaViolationError('{} is not a valid datetime'.format(key))


TYPE_MAP = {
    'string': must_be_type(basestring),
    'str': must_be_type(basestring),
    'int': must_be_type(int),
    'num': must_be_type(int),
    'number': must_be_type(int),
    'date': must_be_date,
    'datetime': must_be_date,
    'bool': must_be_type(bool),
    'dict': must_be_type(dict),
    'object': must_be_type(dict),
    'list': must_be_type(list),
    'email': regex('([^@]+@.+\..+'),
    'doi': doi,
    'ORCID': orcid
}
