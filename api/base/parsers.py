from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from api.base.renderers import JSONAPIRenderer
from api.base.exceptions import JSONAPIException


NO_ATTRIBUTES_ERROR = 'Request must include /data/attributes.'
NO_DATA_ERROR = 'Request must include /data.'
NO_TYPE_ERROR = 'Request must include /data/type.'
NO_ID_ERROR = 'Request must include /data/id.'


class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'
    renderer_class = JSONAPIRenderer

    @staticmethod
    def flatten_data(resource_object, stream, is_list=False):
        """
        Flattens data objects, making attributes fields the same level as id and type.
        """

        if "attributes" not in resource_object and stream.method != 'DELETE':
            raise JSONAPIException(source={'pointer': '/data/attributes'}, detail=NO_ATTRIBUTES_ERROR)

        object_id = resource_object.get('id')
        object_type = resource_object.get('type')

        # For validating type and id for bulk delete:
        if is_list and stream.method == 'DELETE':
            if object_id is None:
                raise JSONAPIException(source={'pointer': '/data/id'}, detail=NO_ID_ERROR)

            if object_type is None:
                raise JSONAPIException(source={'pointer': '/data/type'}, detail=NO_TYPE_ERROR)

        attributes = resource_object.get('attributes')
        parsed = {'id': object_id, 'type': object_type}
        if attributes:
            parsed.update(attributes)

        return parsed

    # Overrides JSONParser
    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        result = super(JSONAPIParser, self).parse(stream, media_type=media_type, parser_context=parser_context)
        if not isinstance(result, dict):
            raise ParseError()
        data = result.get('data', {})

        if data:
            if isinstance(data, list):
                data_collection = []
                for data_object in data:
                    parsed_data = self.flatten_data(data_object, stream, is_list=True)
                    data_collection.append(parsed_data)

                return data_collection

            else:
                return self.flatten_data(data, stream)

        else:
            raise JSONAPIException(source={'pointer': '/data'}, detail=NO_DATA_ERROR)


class JSONAPIParserForRegularJSON(JSONAPIParser):
    """
    Allows same processing as JSONAPIParser to occur for requests with application/json media type.
    """
    media_type = 'application/json'
