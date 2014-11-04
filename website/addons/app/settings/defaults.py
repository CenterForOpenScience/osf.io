from datetime import date
from datetime import datetime


SYSTEM_USERS_UNCRACKABLE_PASSWORD = '12'

TYPE_MAP = {
    'string': basestring,
    'str': basestring,
    'int': int,
    'num': int,
    'number': int,
    'date': date,
    'datetime': datetime,
    'bool': bool,
    'dict': dict,
    'object': dict,
    'list': list
}
