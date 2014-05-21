from . import Field
from ..validators import validate_string

class StringField(Field):

    data_type = basestring
    validate = validate_string