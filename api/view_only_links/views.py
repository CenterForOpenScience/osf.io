from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.response import Response

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.nodes.serializers import NodeSerializer, JSONAPISerializer
from api.registrations.serializers import RegistrationSerializer
from api.view_only_links.serializers import ViewOnlyLinkDetailSerializer, ViewOnlyLinkNodesSerializer

from osf.models import PrivateLink
from osf.utils.permissions import ADMIN

class ViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/view_only_links_read).
    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = ViewOnlyLinkDetailSerializer

    view_category = 'view-only-links'
    view_name = 'view-only-link-detail'

    def get_object(self):
        link_id = self.kwargs['link_id']
        view_only_link = PrivateLink.load(link_id)
        user = get_user_auth(self.request).user

        for node in view_only_link.nodes.all():
            if not node.has_permission(user, ADMIN):
                raise PermissionDenied

        if not view_only_link:
            raise NotFound

        return view_only_link


class ViewOnlyLinkNodes(JSONAPIBaseView, generics.ListAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/view_only_links_node_list).
        """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeSerializer

    view_category = 'view-only-links'
    view_name = 'view-only-link-nodes'

    ordering = ('-modified',)

    def get_serializer_class(self):
        if 'link_id' in self.kwargs:
            view_only_link = PrivateLink.load(self.kwargs['link_id'])
            node = view_only_link.nodes.first()
            if node.is_registration:
                return RegistrationSerializer
            return NodeSerializer
        else:
            return JSONAPISerializer

    def get_queryset(self):
        link_id = self.kwargs['link_id']
        view_only_link = PrivateLink.load(link_id)
        user = get_user_auth(self.request).user

        nodes = []
        for node in view_only_link.nodes.all():
            if not node.has_permission(user, ADMIN):
                raise PermissionDenied
            nodes.append(node)

        return nodes


class ViewOnlyLinkNodesRelationships(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView):
    """
    Relationship Endpoint for VOL -> Nodes Relationship

    Used to set, update, and retrieve the nodes associated with a view only link.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>    # required
                         }]
                       }
        Success:       201 CREATED

        This requires admin permissions on all nodes to be associated with this view only link.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>    # required
                         }]
                       }
        Success:       200 OK

        This requires admin permissions on all nodes to be associated with this view only link.

    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = ViewOnlyLinkNodesSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON)

    view_category = 'view-only-links'
    view_name = 'view-only-link-nodes-relationships'

    def get_object(self):
        link_id = self.kwargs['link_id']
        view_only_link = PrivateLink.load(link_id)
        return {
            'data': view_only_link.nodes.all(),
            'self': view_only_link,
        }

    def create(self, *args, **kwargs):
        try:
            ret = super().create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=HTTP_204_NO_CONTENT)
        return ret
