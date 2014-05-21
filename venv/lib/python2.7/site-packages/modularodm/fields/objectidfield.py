from . import Field
from ..validators import validate_objectid

from bson import ObjectId

class ObjectIdField(Field):

    validate = validate_objectid
    data_type = ObjectId