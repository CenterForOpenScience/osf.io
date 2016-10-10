from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.filters import ODMFilterMixin
from api.base.serializers import JSONAPISerializer
from api.base.utils import get_object_or_error

from api.identifiers.serializers import NodeIdentifierSerializer, RegistrationIdentifierSerializer

from api.nodes.permissions import (
    IsPublic,
    ExcludeWithdrawals,
)

from website.identifiers.model import Identifier
from website.project.model import Node


class IdentifierList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """List of identifiers for a specified node. *Read-only*.

    ##Identifier Attributes

    OSF Identifier entities have the "identifiers" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        category       string                 e.g. 'ark', 'doi'
        value          string                 the identifier value itself

    ##Links

        self: this identifier's detail page

    ##Relationships

    ###Referent

    The identifier is refers to this node.

    ##Actions

    *None*.

    ##Query Params

     Identifiers may be filtered by their category.

    #This Request/Response

    """

    permission_classes = (
        IsPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.IDENTIFIERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationIdentifierSerializer
    node_lookup_url_kwarg = 'node_id'

    view_category = 'identifiers'
    view_name = 'identifier-list'

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

    def get_serializer_class(self):
        if 'node_id' in self.kwargs:
            if self.get_node().is_registration:
                return RegistrationIdentifierSerializer
            return NodeIdentifierSerializer
        return JSONAPISerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return Q('referent', 'eq', self.get_node())

    # overrides ListCreateAPIView
    def get_queryset(self):
        return Identifier.find(self.get_query_from_request())


class IdentifierDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """List of identifiers for a specified node. *Read-only*.


    ##Identifier Attributes

    OSF Identifier entities have the "identifiers" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        category       string                 e.g. 'ark', 'doi'
        value          string                 the identifier value itself

    ##Links

        self: this identifier's detail page

    ##Relationships

    ###Referent

    The identifier is refers to this node.


    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.IDENTIFIERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationIdentifierSerializer
    view_category = 'identifiers'
    view_name = 'identifier-detail'

    def get_serializer_class(self):
        if 'identifier_id' in self.kwargs:
            if self.get_object().referent.is_registration:
                return RegistrationIdentifierSerializer
            return NodeIdentifierSerializer
        return JSONAPISerializer

    def get_object(self):
        return Identifier.load(self.kwargs['identifier_id'])
