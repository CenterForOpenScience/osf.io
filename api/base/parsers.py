import time
import collections
from django.core.exceptions import ImproperlyConfigured
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError, NotAuthenticated

from framework.auth import signing
from api.base.utils import is_bulk_request
from api.base.renderers import JSONAPIRenderer
from api.base.exceptions import JSONAPIException

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
            raise JSONAPIException(
                source={'pointer': 'data/relationships/{}/data/type'.format(related_resource)},
                detail=NO_TYPE_ERROR,
            )

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
        related_resource = list(relationships.keys())[0]
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
        # allow skip type check for legacy api version
        legacy_type_allowed = parser_context.get('legacy_type_allowed', False)
        request_method = parser_context['request'].method

        if is_relationship and request_method == 'POST':
            if not relationships:
                raise JSONAPIException(source={'pointer': '/data/relationships'}, detail=NO_RELATIONSHIPS_ERROR)

        object_id = resource_object.get('id')
        object_type = resource_object.get('type')

        type_required = not (
            legacy_type_allowed and float(parser_context['request'].version) < 2.7 and request_method == 'PATCH'
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
                    for key, value in relationship.items():
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

    def flatten_multiple_relationships(self, parser, relationships):
        rel = {}
        for resource in relationships:
            ret = super(parser, self).flatten_relationships({resource: relationships[resource]})
            if isinstance(ret, list):
                rel[resource] = []
                for item in ret:
                    if item.get('target_type') and item.get('id'):
                        rel[resource].append(item['id'])
            else:
                if ret.get('target_type') and ret.get('id'):
                    rel[resource] = ret['id']
        return rel


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
            float(parser_context['request'].version) < 2.7 and
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
    """
    If edits are made to this class, be sure to check JSONAPIMultipleRelationshipsParserForRegularJSON to see if corresponding
    edits should be made there.
    """
    def flatten_relationships(self, relationships):
        return self.flatten_multiple_relationships(JSONAPIMultipleRelationshipsParser, relationships)


class JSONAPIMultipleRelationshipsParserForRegularJSON(JSONAPIParserForRegularJSON):
    """
    Allows same processing as JSONAPIMultipleRelationshipsParser to occur for requests with application/json media type.
    """
    def flatten_relationships(self, relationships):
        return self.flatten_multiple_relationships(JSONAPIMultipleRelationshipsParserForRegularJSON, relationships)


class HMACSignedParser(JSONParser):

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as JSON. Validates the 'signature' in the payload then returns the resulting data.
        """
        data = super(HMACSignedParser, self).parse(stream, media_type=media_type, parser_context=parser_context)

        try:
            sig = data['signature']
            payload = signing.unserialize_payload(data['payload'])
            exp_time = payload['time']
        except (KeyError, ValueError):
            raise JSONAPIException(detail='Invalid Payload')

        if not signing.default_signer.verify_payload(sig, payload):
            raise NotAuthenticated

        if time.time() > exp_time:
            raise JSONAPIException(detail='Signature has expired')

        return payload

class SearchParser(JSONAPIParser):

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            view = parser_context['view']
        except KeyError:
            raise ImproperlyConfigured('SearchParser requires "view" context.')
        data = super(SearchParser, self).parse(stream, media_type=media_type, parser_context=parser_context)
        if not data:
            raise JSONAPIException(detail='Invalid Payload')

        res = {
            'query': {
                'bool': {},
            },
        }

        sort = parser_context['request'].query_params.get('sort')
        if sort:
            res['sort'] = [{
                sort.lstrip('-'): {
                    'order': 'desc' if sort.startswith('-') else 'asc',
                },
            }]

        try:
            q = data.pop('q')
        except KeyError:
            pass
        else:
            res['query']['bool'].update({
                'must': {
                    'query_string': {
                        'query': q,
                        'fields': view.search_fields,
                    },
                },
            })

        if any(data.values()):
            res['query']['bool'].update({'filter': []})
            for key, val in data.items():
                if val is not None:
                    if isinstance(val, list):
                        res['query']['bool']['filter'].append({'terms': {key: val}})
                    else:
                        res['query']['bool']['filter'].append({'term': {key: val}})
        return res
