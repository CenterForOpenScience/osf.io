
from rest_framework.parsers import JSONParser
from api.base.renderers import JSONAPIRenderer

class JSONAPIParser(JSONParser):
    media_type = 'application/vnd.api+json'
    renderer_class = JSONAPIRenderer
