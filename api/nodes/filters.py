from copy import deepcopy
from distutils.version import StrictVersion

from django.db.models import Q, Exists, OuterRef

from api.base.exceptions import InvalidFilterOperator, InvalidFilterValue
from api.base.filters import ListFilterMixin
from api.base import utils

from osf.models import AbstractNode, NodeRelation, Node, Preprint
from osf.utils import permissions


class NodesFilterMixin(ListFilterMixin):

    def param_queryset(self, query_params, default_queryset):
        filters = self.parse_query_params(query_params)
        auth_user = utils.get_user_auth(self.request)
        if 'filter[preprint]' in query_params:
            query = Preprint.objects.preprint_permissions_query(user=auth_user.user)
            subquery = Preprint.objects.filter(query & Q(deleted__isnull=True) & Q(node=OuterRef('pk')))
            queryset = default_queryset.annotate(preprints_exist=Exists(subquery))
        else:
            queryset = default_queryset

        if filters:
            for key, field_names in filters.items():
                for field_name, operation in field_names.items():
                    # filter[parent]=null
                    if field_name == 'parent' and operation['op'] == 'eq' and not operation['value']:
                        queryset = queryset.get_roots()
                        query_params = deepcopy(query_params)
                        query_params.pop(key)
        return super(NodesFilterMixin, self).param_queryset(query_params, queryset)

    def build_query_from_field(self, field_name, operation):
        if field_name == 'parent':
            if operation['op'] == 'eq':
                if operation['value']:
                    # filter[parent]=<nid>
                    parent = utils.get_object_or_error(AbstractNode, operation['value'], self.request, display_name='parent')
                    node_ids = NodeRelation.objects.filter(parent=parent, is_node_link=False).values_list('child_id', flat=True)
                    return Q(id__in=node_ids)
            elif operation['op'] == 'ne':
                if not operation['value']:
                    # filter[parent][ne]=null
                    child_ids = (
                        NodeRelation.objects.filter(
                            is_node_link=False,
                        )
                        .exclude(parent__type='osf.collection')
                        .exclude(child__is_deleted=True)
                        .values_list('child_id', flat=True)
                    )
                    return Q(id__in=set(child_ids))
                # TODO: support this case in the future:
                # else filter[parent][ne]=<nid>
                raise InvalidFilterValue(detail='Only "null" is accepted as valid input to "filter[parent][ne]"')
            else:
                # filter[parent][gte]=''
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq', 'ne'])

        if field_name == 'root':
            if None in operation['value']:
                raise InvalidFilterValue(value=operation['value'])
            with_as_root_query = Q(root__guids___id__in=operation['value'])
            return ~with_as_root_query if operation['op'] == 'ne' else with_as_root_query

        if field_name == 'preprint':
            preprint_query = (
                Q(preprints_exist=True)
            )
            return preprint_query if utils.is_truthy(operation['value']) else ~preprint_query

        return super(NodesFilterMixin, self).build_query_from_field(field_name, operation)


class UserNodesFilterMixin(NodesFilterMixin):
    def build_query_from_field(self, field_name, operation):
        if field_name == 'current_user_permissions':
            if operation['value'] not in permissions.API_CONTRIBUTOR_PERMISSIONS:
                raise InvalidFilterValue(value=operation['value'])
            perm = operation['value']
            # Filtering UserNodes on the requesting user's permissions to those nodes.
            user = self.request.user

            if user.is_anonymous:
                # Anonymous users have no perms to the current node in current versions, and in
                # older versions, will have read if node is public
                return Q() if StrictVersion(self.request.version) < StrictVersion('2.11') and perm == permissions.READ else Q(id__in=[])
            elif perm == permissions.READ:
                return Q(id__in=self.build_node_list(user, permissions.READ_NODE))
            elif perm == permissions.WRITE:
                return Q(id__in=self.build_node_list(user, permissions.WRITE_NODE))
            elif perm == permissions.ADMIN:
                return Q(id__in=self.build_node_list(user, permissions.ADMIN_NODE))
        return super(UserNodesFilterMixin, self).build_query_from_field(field_name, operation)

    def build_node_list(self, user, perm, with_superuser=False):
        return Node.objects.get_nodes_for_user(user, permission=perm).values_list('id', flat=True)
