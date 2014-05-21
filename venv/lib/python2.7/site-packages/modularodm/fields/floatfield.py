from . import Field
from ..validators import validate_float

class FloatField(Field):

    validate = validate_float
    data_type = float