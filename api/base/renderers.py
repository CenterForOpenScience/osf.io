
from rest_framework.renderers import JSONRenderer

class JSONAPIRenderer(JSONRenderer):
    media_type = 'application/vnd.api+json'
