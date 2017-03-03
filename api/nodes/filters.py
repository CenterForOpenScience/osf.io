import functools
import operator

from modularodm import Q

from api.base.exceptions import InvalidFilterError
from api.base.filters import ODMFilterMixin
from api.base import utils

from osf.models import Node


class NodesListFilterMixin(ODMFilterMixin):

    def _operation_to_query(self, operation):
        # We special case filters on root because root isn't a field; to get the children
        # of a root, we use a custom manager method, Node.objects.get_children, and build
        # a query from that
        if operation['source_field_name'] == 'root':
            child_pks = []
            for root_guid in operation['value']:
                root = utils.get_object_or_error(Node, root_guid, display_name='root')
                child_pks.extend(Node.objects.get_children(root=root, primary_keys=True))
            return Q('id', 'in', child_pks)
        elif operation['source_field_name'] == 'parent_node':
            if operation['value']:
                parent = utils.get_object_or_error(Node, operation['value'], display_name='parent')
                return Q('parent_nodes', 'eq', parent.id)
            else:
                return Q('parent_nodes', 'isnull', True)
        else:
            return super(NodesListFilterMixin, self)._operation_to_query(operation)



class NodePreprintsFilterMixin(ODMFilterMixin):

    def should_parse_special_query_params(self, field_name):
        return field_name == 'preprint'

    def parse_special_query_params(self, field_name, key, value, query):
        op = 'ne' if utils.is_truthy(value) else 'eq'
        query.get(key).update({
            field_name: [{
                'op': op,
                'value': None,
                'source_field_name': 'preprint_file'
            }, {
                'op': op,
                'value': True,
                'source_field_name': '_is_preprint_orphan'
            }, {
                'op': op,
                'value': True,
                'source_field_name': '_has_abandoned_preprint'
            }]
        })
        return query

    def should_convert_special_params_to_odm_query(self, field_name):
        return field_name == 'preprint'

    def convert_special_params_to_odm_query(self, field_name, query_params, key, data):
        if isinstance(data, list):
            if utils.is_falsy(query_params[key]):
                # Use `or` when looking for not-preprints, to include both no file and is_orphaned
                sub_query = functools.reduce(operator.or_, [
                    Q(item['source_field_name'], item['op'], item['value'])
                    for item in data
                ])
            else:
                sub_query = functools.reduce(operator.and_, [
                    Q(item['source_field_name'], item['op'], item['value'])
                    for item in data
                ])
            return sub_query
        else:
            raise InvalidFilterError('Expected type list for field {}, got {}'.format(field_name, type(data)))
