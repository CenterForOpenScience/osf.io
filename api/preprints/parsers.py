from api.base.exceptions import JSONAPIException
from api.base.parsers import (
    JSONAPIParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
    JSONAPIMultipleRelationshipsParser,
    NO_TYPE_ERROR
)


class PreprintDetailMixin(JSONAPIParser):

    def flatten_data(self, resource_object, parser_context, is_list):
        """
           Flattens data objects, making attributes and relationships fields the same level as id and type.
           and check the type requirement.
        """
        request_method = parser_context['request'].method
        object_type = resource_object.get('type')
        
        if parser_context['request'].version >= 2.7 and request_method == 'PATCH':
            if object_type is None:
                raise JSONAPIException(source={'pointer': '/data/type'}, detail=NO_TYPE_ERROR)

        return super(PreprintDetailMixin, self).flatten_data(resource_object, parser_context, is_list)


class PreprintDetailJSONAPIMultipleRelationshipsParser(
    PreprintDetailMixin, JSONAPIMultipleRelationshipsParser
):
    pass


class PreprintDetailJSONAPIMultipleRelationshipsParserForRegularJSON(
    PreprintDetailMixin,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
):
    pass
