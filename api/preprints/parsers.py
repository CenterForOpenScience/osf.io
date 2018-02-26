from api.base.exceptions import JSONAPIException
from api.base.parsers import (
    JSONAPIParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
    JSONAPIMultipleRelationshipsParser,
    NO_RELATIONSHIPS_ERROR,
    NO_ATTRIBUTES_ERROR,
    NO_ID_ERROR,
    NO_TYPE_ERROR
)


class PreprintDetailMixin(JSONAPIParser):

    def flatten_data(self, resource_object, parser_context, is_list):
        """
               Flattens data objects, making attributes and relationships fields the same level as id and type.
               """

        relationships = resource_object.get('relationships')
        is_relationship = parser_context.get('is_relationship')
        attributes_required = parser_context.get('attributes_required', True)
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

        # For validating type and id for bulk delete:
        if is_list and request_method == 'DELETE':
            if object_id is None:
                raise JSONAPIException(source={'pointer': '/data/id'}, detail=NO_ID_ERROR)

            if parser_context['request'].version >= 2.7 and request_method == 'PATCH':
                if object_type is None:
                    raise JSONAPIException(source={'pointer': '/data/type'}, detail=NO_TYPE_ERROR)

        attributes = resource_object.get('attributes')
        parsed = {'id': object_id, 'type': object_type}

        if attributes:
            parsed.update(attributes)

        if relationships:
            relationships = self.flatten_relationships(relationships)
            parsed.update(relationships)

        return parsed


class PreprintDetailJSONAPIMultipleRelationshipsParser(
    PreprintDetailMixin, JSONAPIMultipleRelationshipsParser
):
    pass


class PreprintDetailJSONAPIMultipleRelationshipsParserForRegularJSON(
    PreprintDetailMixin,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
):
    pass
