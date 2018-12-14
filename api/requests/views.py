from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import permissions
from rest_framework.exceptions import NotFound

from api.actions.serializers import PreprintRequestActionSerializer
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error
from api.requests.permissions import NodeRequestPermission, PreprintRequestPermission
from api.requests.serializers import NodeRequestSerializer, PreprintRequestSerializer
from api.providers.permissions import MustBeModerator
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Node, NodeRequest, PreprintRequest, Preprint


class RequestMixin(object):
    serializer_class = None
    request_class = None
    request_display_name = None
    target_class = None
    target_display_name = None
    target_lookup_url_kwarg = None
    request_lookup_url_kwarg = None

    def __get_object(self, object_class, lookup_arg, display_name, check_object_permissions=True):
        obj = get_object_or_error(
            object_class,
            self.kwargs[lookup_arg],
            self.request,
            display_name=display_name,
        )

        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, obj)

        return obj

    def get_request(self, check_object_permissions=True):
        return self.__get_object(self.request_class, self.request_lookup_url_kwarg, self.request_display_name, check_object_permissions=check_object_permissions)

    def get_target(self, check_object_permissions=True):
        return self.__get_object(self.target_class, self.target_lookup_url_kwarg, self.target_display_name, check_object_permissions=check_object_permissions)


class NodeRequestMixin(RequestMixin):
    serializer_class = NodeRequestSerializer
    request_class = NodeRequest
    request_display_name = 'node request'
    target_class = Node
    target_display_name = 'node'
    target_lookup_url_kwarg = 'node_id'
    request_lookup_url_kwarg = 'request_id'


class PreprintRequestMixin(RequestMixin):
    serializer_class = PreprintRequestSerializer
    request_class = PreprintRequest
    request_display_name = 'preprint request'
    target_class = Preprint
    target_display_name = 'preprint'
    target_lookup_url_kwarg = 'preprint_id'
    request_lookup_url_kwarg = 'request_id'


class RequestDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]  # Actual scope checks are done on subview.as_view
    required_write_scopes = [CoreScopes.NULL]
    view_category = 'requests'
    view_name = 'request-detail'

    def get(self, request, *args, **kwargs):
        request_id = self.kwargs['request_id']
        if NodeRequest.objects.filter(_id=request_id).exists():
            return NodeRequestDetail.as_view()(request._request, *args, **kwargs)
        elif PreprintRequest.objects.filter(_id=request_id).exists():
            return PreprintRequestDetail.as_view()(request._request, *args, **kwargs)
        else:
            raise NotFound

class NodeRequestDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeRequestMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        NodeRequestPermission,
    )

    required_read_scopes = [CoreScopes.NODE_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeRequestSerializer

    view_category = 'requests'
    view_name = 'node-request-detail'

    def get_object(self):
        return self.get_request()

class PreprintRequestDetail(JSONAPIBaseView, generics.RetrieveAPIView, PreprintRequestMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintRequestPermission,
    )

    required_read_scopes = [CoreScopes.PREPRINT_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = PreprintRequestSerializer

    view_category = 'requests'
    view_name = 'preprint-request-detail'

    def get_object(self):
        return self.get_request()

class RequestActionList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'requests'
    view_name = 'request-action-list'

    def get(self, request, *args, **kwargs):
        request_id = self.kwargs['request_id']
        if PreprintRequest.objects.filter(_id=request_id).exists():
            return PreprintRequestActionList.as_view()(request._request, *args, **kwargs)
        else:
            raise NotFound

class PreprintRequestActionList(JSONAPIBaseView, generics.ListAPIView, PreprintRequestMixin, ListFilterMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = PreprintRequestActionSerializer

    view_category = 'requests'
    view_name = 'preprint-request-action-list'

    # supports MustBeModerator
    def get_provider(self):
        request_id = self.kwargs['request_id']
        preprint_request = PreprintRequest.load(request_id)
        if preprint_request:
            return preprint_request.target.provider
        raise NotFound

    # overrides ListFilterMixin
    def get_default_queryset(self):
        return self.get_request().actions.all()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
