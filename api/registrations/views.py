from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError, NotFound
from framework.auth.oauth_scopes import CoreScopes

from website.project.model import Q, Node
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

from api.base.serializers import HideIfRetraction
from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationContributorsSerializer,
)

from api.nodes.views import (
    NodeMixin, ODMFilterMixin, NodeContributorsList, NodeRegistrationsList,
    NodeChildrenList, NodeCommentsList, NodeProvidersList, NodeLinksList,
    NodeContributorDetail, NodeFilesList, NodeLinksDetail, NodeFileDetail,
    NodeAlternativeCitationsList, NodeAlternativeCitationDetail, NodeLogList,
    NodeInstitutionDetail, WaterButlerMixin)

from api.registrations.serializers import RegistrationNodeLinksSerializer, RegistrationFileSerializer

from api.nodes.permissions import (
    ContributorOrPublic,
    ReadOnlyIfRegistration,
)
from api.base.utils import get_object_or_error

class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current registration based on the
    current URL. By default, fetches the current registration based on the node_id kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='node'
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection or not node.is_registration:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class RegistrationList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view is a list of all current registrations for which a user
    has access.  A retracted registration will display a limited subset of information, namely, title, description,
    date_created, registration, retracted, date_registered, retraction_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a retraction
    are the contributors.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registrations's detail view are not necessary.  Unregistered nodes cannot be accessed through this endpoint.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             Title of the registered project or component
        description                     string             Description of the registered node
        category                        string             Node category, must be one of the allowed values
        date_created                    iso8601 timestamp  Timestamp that the node was created
        date_modified                   iso8601 timestamp  Timestamp when the node was last updated
        tags                            array of strings   List of tags that describe the registered node
        current_user_permissions        array of strings   List of strings representing the permissions for the current user on this node
        fork                            boolean            Is this project a fork?
        registration                    boolean            Has this project been registered?
        dashboard                       boolean            Is this registered node visible on the user dashboard?
        public                          boolean            Has this registration been made publicly-visible?
        retracted                       boolean            Has this registration been retracted?
        date_registered                 iso8601 timestamp  Timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  When the embargo on this registration will be lifted (if applicable)
        retraction_justification        string             Reasons for retracting the registration
        pending_retraction              boolean            Is this registration pending retraction?
        pending_registration_approval   boolean            Is this registration pending approval?
        pending_embargo_approval        boolean            Is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'registrations'
    view_name = 'registration-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query

    def is_blacklisted(self, query):
        for query_param in query.nodes:
            field_name = getattr(query_param, 'attribute', None)
            if not field_name:
                continue
            field = self.serializer_class._declared_fields.get(field_name)
            if isinstance(field, HideIfRetraction):
                return True
        return False

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        blacklisted = self.is_blacklisted(query)
        nodes = Node.find(query)
        # If attempting to filter on a blacklisted field, exclude retractions.
        if blacklisted:
            non_retracted_list = [node._id for node in nodes if not node.is_retracted]
            non_retracted_nodes = Node.find(Q('_id', 'in', non_retracted_list))
            return non_retracted_nodes
        return nodes


class RegistrationDetail(JSONAPIBaseView, generics.RetrieveAPIView, RegistrationMixin, WaterButlerMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registration's detail view are not necessary. A retracted registration will display a limited subset of information,
    namely, title, description, date_created, registration, retracted, date_registered, retraction_justification, and registration
    supplement. All other fields will be displayed as null. Additionally, the only relationships permitted to be accessed
    for a retracted registration are the contributors.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             Title of the registered project or component
        description                     string             Description of the registered node
        category                        string             Node category, must be one of the allowed values
        date_created                    iso8601 timestamp  Timestamp that the node was created
        date_modified                   iso8601 timestamp  Timestamp when the node was last updated
        tags                            array of strings   List of tags that describe the registered node
        current_user_permissions        array of strings   List of strings representing the permissions for the current user on this node
        fork                            boolean            Is this project a fork?
        registration                    boolean            Has this project been registered?
        dashboard                       boolean            Is this registered node visible on the user dashboard?
        public                          boolean            Has this registration been made publicly-visible?
        retracted                       boolean            Has this registration been retracted?
        date_registered                 iso8601 timestamp  Timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  When the embargo on this registration will be lifted (if applicable)
        retraction_justification        string             Reasons for retracting the registration
        pending_retraction              boolean            Is this registration pending retraction?
        pending_registration_approval   boolean            Is this registration pending approval?
        pending_embargo_approval        boolean            Is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

        self:  the canonical api endpoint of this registration
        html:  this registration's page on the OSF website

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationDetailSerializer
    view_category = 'registrations'
    view_name = 'registration-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        registration = self.get_node()
        if not registration.is_registration:
            raise ValidationError('This is not a registration.')
        return registration


class RegistrationContributorsList(NodeContributorsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-contributors'

    def get_serializer_class(self):
        return RegistrationContributorsSerializer


class RegistrationContributorDetail(NodeContributorDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-contributor-detail'
    serializer_class = RegistrationContributorsSerializer


class RegistrationChildrenList(NodeChildrenList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-children'
    serializer_class = RegistrationSerializer

    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query


class RegistrationCommentsList(NodeCommentsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-comments'


class RegistrationLogList(NodeLogList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-logs'


class RegistrationProvidersList(NodeProvidersList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-providers'


class RegistrationNodeLinksList(NodeLinksList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-pointers'
    serializer_class = RegistrationNodeLinksSerializer


class RegistrationNodeLinksDetail(NodeLinksDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-pointer-detail'
    serializer_class = RegistrationNodeLinksSerializer


class RegistrationRegistrationsList(NodeRegistrationsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-providers'


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-files'
    serializer_class = RegistrationFileSerializer


class RegistrationFileDetail(NodeFileDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-file-detail'
    serializer_class = RegistrationFileSerializer


class RegistrationAlternativeCitationsList(NodeAlternativeCitationsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-alternative-citations'


class RegistrationAlternativeCitationDetail(NodeAlternativeCitationDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-alternative-citation-detail'


class RegistrationInstitutionDetail(NodeInstitutionDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-institution-detail'
