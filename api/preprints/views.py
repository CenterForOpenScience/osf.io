from rest_framework import generics
from rest_framework import permissions as drf_permissions

from modularodm import Q

from framework.auth.oauth_scopes import CoreScopes

from website.models import User, Node

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin, ListFilterMixin
from .serializers import PreprintSerializer, PreprintDetailSerializer
from api.nodes.views import NodeMixin, WaterButlerMixin
from api.base.utils import get_user_auth, is_bulk_request
from website.exceptions import NodeStateError
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from api.base.pagination import NodeContributorPagination
from api.base import generic_bulk_views as bulk_views
from api.nodes.serializers import (
    NodeContributorsSerializer,
    NodeContributorDetailSerializer,
    NodeContributorsCreateSerializer
)
# TODO: Possibly write a PreprintMixin class? Right now using node mixin requires the urls to specify a <node_id>
class PreprintList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = PreprintSerializer

    ordering = ('-date_registered')
    view_category = 'preprints'
    view_name = 'preprint-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('preprint_file', 'neq', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return Node.find(query)

class PreprintDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, NodeMixin, WaterButlerMixin):
    #permission_classes = (
    #    drf_permissions.IsAuthenticatedOrReadOnly,
    #    ContributorOrPublic,
    #    ReadOnlyIfRegistration,
    #    base_permissions.TokenHasScope,
    #    ExcludeWithdrawals,
    #)

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = PreprintDetailSerializer
    view_category = 'preprints'
    view_name = 'preprint-detail'

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_node()

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_object()
        try:
            node.remove_node(auth=auth)
        except NodeStateError as err:
            raise ValidationError(err.message)
        node.save()

class PreprintAuthorsList(JSONAPIBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, ListFilterMixin, NodeMixin):
    # Taken from NodeContributorsList
    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]
    model_class = User

    pagination_class = NodeContributorPagination
    serializer_class = NodeContributorsSerializer
    view_category = 'preprints'
    view_name = 'preprint-authors'

    def get_default_queryset(self):
        node = self.get_node()
        visible_contributors = set(node.visible_contributor_ids)
        contributors = []
        for contributor in node.contributors:
            contributor.bibliographic = contributor._id in visible_contributors
            contributor.permission = node.get_permissions(contributor)[-1]
            contributor.node_id = node._id
            contributors.append(contributor)
        return contributors

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView, BulkDeleteJSONAPIView
    def get_serializer_class(self):
        """
        Use NodeContributorDetailSerializer which requires 'id'
        """
        if self.request.method == 'PUT' or self.request.method == 'PATCH' or self.request.method == 'DELETE':
            return NodeContributorDetailSerializer
        elif self.request.method == 'POST':
            return NodeContributorsCreateSerializer
        else:
            return NodeContributorsSerializer

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        queryset = self.get_queryset_from_request()

        # If bulk request, queryset only contains contributors in request
        if is_bulk_request(self.request):
            contrib_ids = [item['id'] for item in self.request.data]
            queryset[:] = [contrib for contrib in queryset if contrib._id in contrib_ids]
        return queryset

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(PreprintAuthorsList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_node()
        if len(node.visible_contributors) == 1 and node.get_visible(instance):
            raise ValidationError('Must have at least one visible contributor')
        if instance not in node.contributors:
            raise NotFound('User cannot be found in the list of contributors.')
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError('Must have at least one registered admin contributor')