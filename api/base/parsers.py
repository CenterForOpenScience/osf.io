
from rest_framework.parsers import JSONParser
from api.base.renderers import JSONAPIRenderer

class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data. Overrides media_type.
    """
    media_type = 'application/vnd.api+json; ext="bulk"'
    renderer_class = JSONAPIRenderer
