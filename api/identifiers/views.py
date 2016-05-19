from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound


from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error

from api.identifiers.serializers import IdentifierSerializer

from api.nodes.permissions import (
    IsPublic,
    ExcludeWithdrawals,
)

from website.models import Node
from website.identifiers.model import Identifier


class IdentifierList(JSONAPIBaseView, generics.ListAPIView):
    """List of identifiers for a specified node. *Read-only*.

   ##Identifier Attributes

    OSF License entities have the "licenses" `type`.
        name           type                   description
        ----------------------------------------------------------------------------
        category       string                 e.g. 'ark', 'doi'
        referent       link                   object to which the identifier points
        value          string                 the identifier value itself

    ##Links
    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions
    *None*.

    ##Query Params
     *None*.

    #This Request/Response

    """

    permission_classes = (
        IsPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    serializer_class = IdentifierSerializer

    view_category = 'nodes'
    view_name = 'node-identifier-list'
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='node'
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node

    # overrides ListCreateAPIView
    def get_queryset(self):
        return Identifier.find(Q('referent', 'eq', self.get_node()))


class IdentifierDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Identifiers detail for the requested identifier. Read only

    Detail for any identifier attached to a node, including a link back to the node.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]

    serializer_class = IdentifierSerializer
    view_category = 'identifiers'
    view_name = 'node-identifier-detail'

    def get_object(self):
        identifier = self.kwargs['node_identifier']
        return Identifier.find_one(Q('value', 'eq', identifier))
