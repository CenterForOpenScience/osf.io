import re
from datetime import date
from datetime import datetime
from functools import partial

import requests

from website.addons.app.exceptions import SchemaViolationError

DOI_HEADERS = {'Accept': 'application/json'}


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

def doi(key, doi):
    '''TODO Write a doc string
    '''
    try:
        ret = requests.get(doi, headers=DOI_HEADERS)
    except Exception:
        raise SchemaViolationError('{} at key {} is not a valid doi'.format(doi, key))

    if ret.status_code != 200:
        raise SchemaViolationError('{} at key {} is not a valid doi'.format(doi, key))
    return ret.json()


TYPE_MAP = {
    'string': must_be_type(basestring),
    'str': must_be_type(basestring),
    'int': must_be_type(int),
    'num': must_be_type(int),
    'number': must_be_type(int),
    'date': date,
    'datetime': datetime,
    'bool': must_be_type(bool),
    'dict': must_be_type(dict),
    'object': must_be_type(dict),
    'list': must_be_type(list),
    'email': regex('([^@]+@.+\..+'),
    'doi': doi
}
