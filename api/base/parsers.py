import collections
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError

from api.base.utils import is_bulk_request
from api.base.renderers import JSONAPIRenderer
from api.base.exceptions import JSONAPIException

NO_ATTRIBUTES_ERROR = 'Request must include /data/attributes.'
NO_RELATIONSHIPS_ERROR = 'Request must include /data/relationships.'
NO_DATA_ERROR = 'Request must include /data.'
NO_TYPE_ERROR = 'Request must include /type.'
NO_ID_ERROR = 'Request must include /data/id.'


class JSONAPIParser(JSONParser):
    """
    Parses JSON-serialized data. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'
    renderer_class = JSONAPIRenderer

    @staticmethod
    def get_relationship(data, related_resource):
        target_type = data.get('type')
        if not target_type:
            raise JSONAPIException(source={'pointer': 'data/relationships/{}/data/type'.format(related_resource)},
                                   detail=NO_TYPE_ERROR)

        id = data.get('id')
        return {'id': id, 'target_type': target_type}

    # Overrides JSONParser
    def flatten_relationships(self, relationships):
        """
        Flattens relationships dictionary which has information needed to create related resource objects.

        Validates that formatting of relationships dictionary is correct.
        """
        if not isinstance(relationships, dict):
            raise ParseError()

        # Can only create one type of relationship.
        related_resource = relationships.keys()[0]
        if not isinstance(relationships[related_resource], dict) or related_resource == 'data':
            raise ParseError()
        data = relationships[related_resource].get('data')

        if not data:
            raise JSONAPIException(source={'pointer': 'data/relationships/{}/data'.format(related_resource)}, detail=NO_DATA_ERROR)

        if isinstance(data, list):
            return [self.get_relationship(item, related_resource) for item in data]
        else:
            return self.get_relationship(data, related_resource)

    def flatten_data(self, resource_object, parser_context, is_list):
        """
        Flattens data objects, making attributes and relationships fields the same level as id and type.
        """

        relationships = resource_object.get('relationships')
        is_relationship = parser_context.get('is_relationship')
        attributes_required = parser_context.get('attributes_required', True)
        # allow skip type check for legacy api version
        legacy_type_allowed = parser_context.get('legacy_type_allowed', False)
        request_method = parser_context['request'].method

        # Request must include "relationships" or "attributes"
        if is_relationship and request_method == 'POST':
            if not relationships:
                raise JSONAPIException(source={'pointer': '/data/relationships'}, detail=NO_RELATIONSHIPS_ERROR)
        else:
            if 'attributes' not in resource_object and attributes_required and request_method != 'DELETE':
                raise JSONAPIException(source={'pointer': '/data/attributes'}, detail=NO_ATTRIBUTES_ERROR)

        object_id = resource_object.get('id')
        object_type = resource_object.get('type')

        type_required = not (
            legacy_type_allowed and parser_context['request'].version < 2.7 and request_method == 'PATCH'
        )

        # For validating type and id for bulk delete:
        if is_list and request_method == 'DELETE':
            if object_id is None:
                raise JSONAPIException(source={'pointer': '/data/id'}, detail=NO_ID_ERROR)

            if type_required and object_type is None:
                raise JSONAPIException(source={'pointer': '/data/type'}, detail=NO_TYPE_ERROR)

        attributes = resource_object.get('attributes')
        parsed = {'id': object_id, 'type': object_type}

        if attributes:
            parsed.update(attributes)

        if relationships:
            relationships = self.flatten_relationships(relationships)
            if isinstance(relationships, list):
                relationship_values = []
                relationship_key = None
                for relationship in relationships:
                    for key, value in relationship.iteritems():
                        relationship_values.append(value)
                        relationship_key = key
                relationship = {relationship_key: relationship_values}
                parsed.update(relationship)
            else:
                parsed.update(relationships)

        return parsed

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON and returns the resulting data.
        """
        result = super(JSONAPIParser, self).parse(stream, media_type=media_type, parser_context=parser_context)

        if not isinstance(result, dict):
            raise ParseError()
        data = result.get('data', {})

        if data:
            if is_bulk_request(parser_context['request']):
                if not isinstance(data, list):
                    raise ParseError('Expected a list of items but got type "dict".')

                data_collection = []
                data_collection.extend([self.flatten_data(data_object, parser_context, is_list=True) for data_object in data])

                return data_collection

            else:
                if not isinstance(data, collections.Mapping):
                    raise ParseError('Expected a dictionary of items.')
                return self.flatten_data(data, parser_context, is_list=False)

        else:
            raise JSONAPIException(source={'pointer': '/data'}, detail=NO_DATA_ERROR)


class JSONAPIParserForRegularJSON(JSONAPIParser):
    """
    Allows same processing as JSONAPIParser to occur for requests with application/json media type.
    """
    media_type = 'application/json'

class JSONAPIRelationshipParser(JSONParser):
    """
    Parses JSON-serialized data for relationship endpoints. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'

    def parse(self, stream, media_type=None, parser_context=None):
        res = super(JSONAPIRelationshipParser, self).parse(stream, media_type, parser_context)

        if not isinstance(res, dict):
            raise ParseError('Request body must be dictionary')
        data = res.get('data')

        if data:
            if not isinstance(data, list):
                raise ParseError('Data must be an array')
            for i, datum in enumerate(data):

                if datum.get('id') is None:
                    raise JSONAPIException(source={'pointer': '/data/{}/id'.format(str(i))}, detail=NO_ID_ERROR)

                if datum.get('type') is None:
                    raise JSONAPIException(source={'pointer': '/data/{}/type'.format(str(i))}, detail=NO_TYPE_ERROR)

            return {'data': data}

        return {'data': []}


class JSONAPIRelationshipParserForRegularJSON(JSONAPIRelationshipParser):
    """
    Allows same processing as JSONAPIRelationshipParser to occur for requests with application/json media type.
    """
    media_type = 'application/json'


class JSONAPIOnetoOneRelationshipParser(JSONParser):
    """
    Parses JSON-serialized data for relationship endpoints. Overrides media_type.
    """
    media_type = 'application/vnd.api+json'

    def parse(self, stream, media_type=None, parser_context=None):
        res = super(JSONAPIOnetoOneRelationshipParser, self).parse(stream, media_type, parser_context)

        if not isinstance(res, dict):
            raise ParseError('Request body must be dictionary')
        data = res.get('data')
        # allow skip type check for legacy api version
        legacy_type_allowed = parser_context.get('legacy_type_allowed', True)
        type_required = not (
            legacy_type_allowed and
            parser_context['request'].version < 2.7 and
            parser_context['request'].method == 'PATCH'
        )
        if data:
            id_ = data.get('id')
            type_ = data.get('type')

            if id_ is None:
                raise JSONAPIException(source={'pointer': '/data/id'}, detail=NO_ID_ERROR)

            if type_required and type_ is None:
                raise JSONAPIException(source={'pointer': '/data/type'}, detail=NO_TYPE_ERROR)

            return data

        return {'type': None, 'id': None}


class JSONAPIOnetoOneRelationshipParserForRegularJSON(JSONAPIOnetoOneRelationshipParser):
    """
    Allows same processing as JSONAPIRelationshipParser to occur for requests with application/json media type.
    """
    media_type = 'application/json'


class JSONAPIMultipleRelationshipsParser(JSONAPIParser):
    def flatten_relationships(self, relationships):
        rel = {}
        for resource in relationships:
            ret = super(JSONAPIMultipleRelationshipsParser, self).flatten_relationships({resource: relationships[resource]})
            if isinstance(ret, list):
                rel = []
                for item in ret:
                    if item.get('target_type') and item.get('id'):
                        rel.append({resource: item['id']})
            else:
                if ret.get('target_type') and ret.get('id'):
                    rel[resource] = ret['id']
        return rel


class JSONAPIMultipleRelationshipsParserForRegularJSON(JSONAPIParserForRegularJSON):
    def flatten_relationships(self, relationships):
        ret = super(JSONAPIMultipleRelationshipsParserForRegularJSON, self).flatten_relationships(relationships)
        related_resource = relationships.keys()[0]
        if ret.get('target_type') and ret.get('id'):
            return {related_resource: ret['id']}
        return ret
