from rest_framework import generics, permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from website.project.model import Q, Node
from api.base import permissions as base_permissions

from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer
)

from api.nodes.views import NodeMixin, ODMFilterMixin
from api.nodes.permissions import (
    ContributorOrPublic,
    ReadOnlyIfRegistration)


class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current registration based on the
    current URL. By default, fetches the current node based on the registration_id kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'registration_id'


class RegistrationList(generics.ListAPIView, ODMFilterMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view is a list of all current registrations for which a user
    has access.

    Paginated list of registrations are ordered by their `date_modified`.  Each resource contains the full representation of the
    registration, meaning additional requests to an individual registrations's detail view are not necessary.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name               type               description
        ---------------------------------------------------------------------------------
        title              string             title of the registered project or component
        description        string             description of the registered node
        category           string             node category, must be one of the allowed values
        date_created       iso8601 timestamp  timestamp that the node was created
        date_modified      iso8601 timestamp  timestamp when the node was last updated
        tags               array of strings   list of tags that describe the registered node
        fork               boolean            is this project a fork?
        registration       boolean            has this project been registered?
        collection         boolean            is this registered node a collection of other nodes?
        dashboard          boolean            is this registered node visible on the user dashboard?
        public             boolean            has this registration been made publicly-visible?
        retracted          boolean            has this registration been retracted?
        date_registered    iso8601 timestamp  timestamp that the registration was created

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###
    ###
    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = RegistrationSerializer

    ordering = ('-date_modified', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))

        query = base_query & permission_query
        return query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)


class RegistrationDetail(generics.RetrieveAPIView, RegistrationMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Paginated list of registrations ordered by their `date_modified`.  Each resource contains the full representation of the
    registration, meaning additional requests to an individual registrations's detail view are not necessary.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name               type               description
        ---------------------------------------------------------------------------------
        title              string             title of the registered project or component
        description        string             description of the registered node
        category           string             node category, must be one of the allowed values
        date_created       iso8601 timestamp  timestamp that the node was created
        date_modified      iso8601 timestamp  timestamp when the node was last updated
        tags               array of strings   list of tags that describe the registered node
        fork               boolean            is this project a fork?
        registration       boolean            has this project been registered?
        collection         boolean            is this registered node a collection of other nodes?
        dashboard          boolean            is this registered node visible on the user dashboard?
        public             boolean            has this registration been made publicly-visible?
        retracted          boolean            has this registration been retracted?
        date_registered    iso8601 timestamp  timestamp that the registration was created

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ##Links

        self:  the canonical api endpoint of this registration
        html:  this registration's page on the OSF website

    ##Actions

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = RegistrationDetailSerializer

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_node()

    # overrides RetrieveUpdateDestroyAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        # TODO: The method it overrides already returns request (plus more stuff). Why does this method exist?
        return {'request': self.request}
