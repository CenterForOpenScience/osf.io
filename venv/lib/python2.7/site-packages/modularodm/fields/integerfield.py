from . import Field
from ..validators import validate_integer

class IntegerField(Field):

    # default = None
    validate = validate_integer
    data_type = int