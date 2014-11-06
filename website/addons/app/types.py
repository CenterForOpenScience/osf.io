import re
from datetime import date
from datetime import datetime
from functools import partial

from website.addons.app.exceptions import SchemaViolationError


def _must_be_type(_type, key, value):
    if not isinstance(value, _type):
        raise SchemaViolationError('{} must be of type {}'.format(key, _type))
    return value


def _regex(rgx, key, value):
    if isinstance(value, basestring) and re.compile(rgx).search(value):
        return value
    raise SchemaViolationError('{} must follow the pattern {}'.format(key, rgx))


regex = lambda x: partial(_regex, x)
def must_be_type(_type):
    ret = lambda x: partial(_must_be_type, x)
    ret.__doc__ = str(_type)
    return ret


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
    'email': regex('([^@]+@.+\..+')
}
