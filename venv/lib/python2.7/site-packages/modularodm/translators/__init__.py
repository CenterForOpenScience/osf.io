from dateutil import parser as dateparser
from bson import ObjectId

class DefaultTranslator(object):

    null_value = None

    to_default = None
    from_default = None

class JSONTranslator(DefaultTranslator):

    def to_datetime(self, value):
        return str(value)

    def from_datetime(self, value):
        return dateparser.parse(value)

    def to_ObjectId(self, value):
        return str(value)

    def from_ObjectId(self, value):
        return ObjectId(value)

class StringTranslator(JSONTranslator):

    null_value = 'none'

    def to_default(self, value):
        return str(value)

    def from_int(self, value):
        return int(value)

    def from_float(self, value):
        return float(value)

    def from_bool(self, value):
        return bool(value)