from . import Field
from ..validators import validate_boolean

class BooleanField(Field):

    validate = validate_boolean
    data_type = bool