from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from api.base.renderers import JSONAPIRenderer
from api.base.exceptions import JSONAPIException

NO_ATTRIBUTES_ERROR = 'Request must include /data/attributes.'
NO_RELATIONSHIPS_ERROR = 'Request must include /data/relationships.'
NO_DATA_ERROR = 'Request must include /data.'
NO_TYPE_ERROR = 'Request must include /type.'


class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'
    renderer_class = JSONAPIRenderer

    def flatten_relationships(self, relationships):
        """
        Flattens relationships dictionary which has information needed to create related resource objects.

        Validates that formatting of relationships dictionary is correct.
        """
        if not isinstance(relationships, dict):
            raise ParseError()
        related_resource = relationships.keys()[0]
        if not isinstance(relationships[related_resource], dict) or related_resource == 'data':
            raise ParseError()
        data = relationships[related_resource].get('data')

        if not data:
            raise JSONAPIException(source={'pointer': 'data/relationships/<related_resource_name>/data'}, detail=NO_DATA_ERROR)

        target_type = data.get('type')
        if not target_type:
            raise JSONAPIException(source={'pointer': 'data/relationships/<related_resource_name>/data/type'}, detail=NO_TYPE_ERROR)

        id = data.get('id')
        return {'id': id, 'target_type': target_type}

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data
        """
        result = super(JSONAPIParser, self).parse(stream, media_type=media_type, parser_context=parser_context)
        if not isinstance(result, dict):
            raise ParseError()
        data = result.get('data', {})

        if data:
            relationships = data.get('relationships')

            path = stream.path
            related_resources = ['contributors', 'node_links']

            # Request must include "relationships" or "attributes"
            if stream.method == 'POST' and (related_resources[0] in path or related_resources[1] in path):
                if not relationships:
                    raise JSONAPIException(source={'pointer': '/data/relationships'}, detail=NO_RELATIONSHIPS_ERROR)
            else:
                if 'attributes' not in data:
                    raise JSONAPIException(source={'pointer': '/data/attributes'}, detail=NO_ATTRIBUTES_ERROR)

            id = data.get('id')
            object_type = data.get('type')
            attributes = data.get('attributes')

            parsed = {'id': id, 'type': object_type}

            if attributes:
                parsed.update(attributes)

            if relationships:
                relationships = self.flatten_relationships(relationships)
                parsed.update(relationships)

            return parsed

        else:
            raise JSONAPIException(source={'pointer': '/data'}, detail=NO_DATA_ERROR)


class JSONAPIParserForRegularJSON(JSONAPIParser):
    media_type = 'application/json'
