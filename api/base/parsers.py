from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from api.base.renderers import JSONAPIRenderer
from api.base.exceptions import JSONAPIException


NO_ATTRIBUTES_ERROR = 'Request must include /data/attributes.'
NO_DATA_ERROR = 'Request must include /data.'

class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'
    renderer_class = JSONAPIRenderer

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data
        """
        result = super(JSONAPIParser, self).parse(stream, media_type=media_type, parser_context=parser_context)
        if not isinstance(result, dict):
            raise ParseError()
        data = result.get('data', {})
        
        def data_flattener(resource_object, stream):
            if "attributes" not in resource_object and stream.method != 'DELETE':
                    raise JSONAPIException(source={'pointer': '/data/attributes'}, detail=NO_ATTRIBUTES_ERROR)
            id = resource_object.get('id')
            object_type = resource_object.get('type')
            attributes = resource_object.get('attributes')

            parsed = {'id': id, 'type': object_type}
            if attributes:
                parsed.update(attributes)

            return parsed
        
        
        if data:
            if isinstance(data, list):
                data_collection = []
                for object in data:
                    parsed_data = data_flattener(object, stream)
                    data_collection.append(parsed_data)
                return data_collection

            else:
                return data_flattener(data, stream)

        else:
            raise JSONAPIException(source={'pointer': '/data'}, detail=NO_DATA_ERROR)


class JSONAPIParserForRegularJSON(JSONAPIParser):
    media_type = 'application/json'
