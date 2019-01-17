from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from framework.auth.oauth_scopes import CoreScopes

from osf.models import AbstractNode, Registration
from api.base import permissions as base_permissions
from api.base import generic_bulk_views as bulk_views
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView, BaseContributorDetail, BaseContributorList, BaseNodeLinksDetail, BaseNodeLinksList, WaterButlerMixin

from api.base.serializers import HideIfWithdrawal, LinkedRegistrationsRelationshipSerializer
from api.base.serializers import LinkedNodesRelationshipSerializer
from api.base.pagination import NodeContributorPagination
from api.base.parsers import JSONAPIRelationshipParser
from api.base.parsers import JSONAPIRelationshipParserForRegularJSON
from api.base.utils import get_user_auth, default_node_list_permission_queryset, is_bulk_request, is_truthy
from api.comments.serializers import RegistrationCommentSerializer, CommentCreateSerializer
from api.identifiers.serializers import RegistrationIdentifierSerializer
from api.nodes.views import NodeIdentifierList
from api.users.views import UserMixin

from api.nodes.permissions import (
    ReadOnlyIfRegistration,
    ContributorDetailPermissions,
    ContributorOrPublic,
    ContributorOrPublicForRelationshipPointers,
    AdminOrPublic,
    ExcludeWithdrawals,
    NodeLinksShowIfVersion,
)
from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationContributorsSerializer,
    RegistrationProviderSerializer
)

from api.nodes.filters import NodesFilterMixin

from api.nodes.views import (
    NodeMixin, NodeRegistrationsList, NodeLogList,
    NodeCommentsList, NodeProvidersList, NodeFilesList, NodeFileDetail,
    NodeInstitutionsList, NodeForksList, NodeWikiList, LinkedNodesList,
    NodeViewOnlyLinksList, NodeViewOnlyLinkDetail, NodeCitationDetail, NodeCitationStyleDetail,
    NodeLinkedRegistrationsList,
)

from api.registrations.serializers import RegistrationNodeLinksSerializer, RegistrationFileSerializer
from api.wikis.serializers import RegistrationWikiSerializer

from api.base.utils import get_object_or_error


class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current registration based on the
    current URL. By default, fetches the current registration based on the node_id kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            AbstractNode,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
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


class RegistrationList(JSONAPIBaseView, generics.ListAPIView, bulk_views.BulkUpdateJSONAPIView, NodesFilterMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view is a list of all current registrations for which a user
    has access.  A withdrawn registration will display a limited subset of information, namely, title, description,
    created, registration, withdrawn, date_registered, withdrawal_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a withdrawn
    registration are the contributors - other relationships will return a 403.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registrations's detail view are not necessary.  Unregistered nodes cannot be accessed through this endpoint.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
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

    ordering = ('-modified',)
    model_class = Registration

    # overrides BulkUpdateJSONAPIView
    def get_serializer_class(self):
        """
        Use RegistrationDetailSerializer which requires 'id'
        """
        if self.request.method in ('PUT', 'PATCH'):
            return RegistrationDetailSerializer
        else:
            return RegistrationSerializer

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        return default_node_list_permission_queryset(user=self.request.user, model_cls=Registration)

    def is_blacklisted(self):
        query_params = self.parse_query_params(self.request.query_params)
        for key, field_names in query_params.iteritems():
            for field_name, data in field_names.iteritems():
                field = self.serializer_class._declared_fields.get(field_name)
                if isinstance(field, HideIfWithdrawal):
                    return True
        return False

    # overrides ListAPIView, ListBulkCreateJSONAPIView
    def get_queryset(self):
        # For bulk requests, queryset is formed from request body.
        if is_bulk_request(self.request):
            auth = get_user_auth(self.request)
            registrations = Registration.objects.filter(guids___id__in=[registration['id'] for registration in self.request.data])

            # If skip_uneditable=True in query_params, skip nodes for which the user
            # does not have EDIT permissions.
            if is_truthy(self.request.query_params.get('skip_uneditable', False)):
                has_permission = registrations.filter(contributor__user_id=auth.user.id, contributor__write=True).values_list('guids___id', flat=True)
                return Registration.objects.filter(guids___id__in=has_permission)

            for registration in registrations:
                if not registration.can_edit(auth):
                    raise PermissionDenied
            return registrations
        blacklisted = self.is_blacklisted()
        registrations = self.get_queryset_from_request()
        # If attempting to filter on a blacklisted field, exclude withdrawals.
        if blacklisted:
            return registrations.exclude(retraction__isnull=False)
        return registrations


class RegistrationDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, RegistrationMixin, WaterButlerMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registration's detail view are not necessary. A withdrawn registration will display a limited subset of information,
    namely, title, description, created, registration, withdrawn, date_registered, withdrawal_justification, and
    registration supplement. All other fields will be displayed as null. Additionally, the only relationships permitted
    to be accessed for a withdrawn registration are the contributors - other relationships will return a 403.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "registrations",   # required
                           "id":   {registration_id}, # required
                           "attributes": {
                             "public": true           # required
                           }
                         }
                       }
        Success:       200 OK + node representation

    To turn a registration from private to public, issue either a PUT or a PATCH request against the `/links/self` URL.
    Registrations can only be turned from private to public, not vice versa.  The "public" field is the only field that can
    be modified on a registration and you must have admin permission to do so.

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

        self:  the canonical api endpoint of this registration
        html:  this registration's page on the GakuNin RDM website

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        AdminOrPublic,
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


class RegistrationContributorsList(BaseContributorList, RegistrationMixin, UserMixin):
    """Contributors (users) for a registration.

    Contributors are users who can make changes to the node or, in the case of private nodes,
    have read access to the node. Contributors are divided between 'bibliographic' and 'non-bibliographic'
    contributors. From a permissions standpoint, both are the same, but bibliographic contributors
    are included in citations, while non-bibliographic contributors are not included in citations.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed and the id for
    the contributor will be an empty string.

    ##Node Contributor Attributes

    <!--- Copied Attributes from NodeContributorDetail -->

    `type` is "contributors"

        name                        type     description
        ======================================================================================================
        bibliographic               boolean  Whether the user will be included in citations for this node. Default is true.
        permission                  string   User permission level. Must be "read", "write", or "admin". Default is "write".
        unregistered_contributor    string   Contributor's assigned name if contributor hasn't yet claimed account

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Relationships

    ###Users

    This endpoint shows the contributor user detail and is automatically embedded.

    ##Actions

    ###Adding Contributors

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON): {
                      "data": {
                        "type": "contributors",                   # required
                        "attributes": {
                          "bibliographic": true|false,            # optional
                          "permission": "read"|"write"|"admin"    # optional
                        },
                        "relationships": {
                          "users": {
                            "data": {
                              "type": "users",                    # required
                              "id":   "{user_id}"                 # required
                            }
                        }
                    }
                }
            }
        Success:       201 CREATED + node contributor representation

    Add a contributor to a node by issuing a POST request to this endpoint.  This effectively creates a relationship
    between the node and the user.  Besides the top-level type, there are optional "attributes" which describe the
    relationship between the node and the user. `bibliographic` is a boolean and defaults to `true`.  `permission` must
    be a [valid OSF permission key](/v2/#osf-node-permission-keys) and defaults to `"write"`.  A relationship object
    with a "data" member, containing the user `type` and user `id` must be included.  The id must be a valid user id.
    All other fields not listed above will be ignored.  If the request is successful the API will return
    a 201 response with the representation of the new node contributor in the body.  For the new node contributor's
    canonical URL, see the `/links/self` field of the response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    NodeContributors may be filtered by `bibliographic`, or `permission` attributes.  `bibliographic` is a boolean, and
    can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true` or `false` in
    the query will cause the match to fail regardless.

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` of the user entities so that it points to
    the user's profile image scaled to the given size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response
    """
    view_category = 'registrations'
    view_name = 'registration-contributors'

    pagination_class = NodeContributorPagination
    serializer_class = RegistrationContributorsSerializer

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    def get_default_queryset(self):
        node = self.get_node(check_object_permissions=False)
        return node.contributor_set.all().include('user__guids')


class RegistrationContributorDetail(BaseContributorDetail, RegistrationMixin, UserMixin):
    """Detail of a contributor for a registration.

    Contributors are users who can make changes to the node or, in the case of private nodes,
    have read access to the node. Contributors are divided between 'bibliographic' and 'non-bibliographic'
    contributors. From a permissions standpoint, both are the same, but bibliographic contributors
    are included in citations, while non-bibliographic contributors are not included in citations.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed and the id for
    the contributor will be an empty string.

    Contributors can be viewed, removed, and have their permissions and bibliographic status changed via this
    endpoint.

    ##Attributes

    `type` is "contributors"

        name                        type     description
        ======================================================================================================
        bibliographic               boolean  Whether the user will be included in citations for this node. Default is true.
        permission                  string   User permission level. Must be "read", "write", or "admin". Default is "write".
        unregistered_contributor    string   Contributor's assigned name if contributor hasn't yet claimed account

    ###Users

    This endpoint shows the contributor user detail.

    ##Links

        self:           the canonical api endpoint of this contributor
        html:           the contributing user's page on the GakuNin RDM website
        profile_image:  a url to the contributing user's profile image

    ##Query Params

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` so that it points the image scaled to the given
    size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response

    """
    view_category = 'registrations'
    view_name = 'registration-contributor-detail'
    serializer_class = RegistrationContributorsSerializer

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

class RegistrationChildrenList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, RegistrationMixin):
    """Children of the current registration.

    This will get the next level of child nodes for the selected node if the current user has read access for those
    nodes. Creating a node via this endpoint will behave the same as the [node list endpoint](/v2/nodes/), but the new
    node will have the selected node set as its parent.

    ##Node Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name                            type                description
        =================================================================================
        title                           string              title of project or component
        description                     string              description of the node
        category                        string              node category, must be one of the allowed values
        date_created                    iso8601 timestamp   timestamp that the node was created
        date_modified                   iso8601 timestamp   timestamp when the node was last updated
        tags                            array of strings    list of tags that describe the node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings    list of strings representing the permissions for the current user on this node
        registration                    boolean             is this a registration? (always false - may be deprecated in future versions)
        fork                            boolean             is this node a fork of another node?
        public                          boolean             has this node been made publicly-visible?
        collection                      boolean             is this a collection? (always false - may be deprecated in future versions)

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `id`, `title`, `category`, `description`, `public`, `tags`, `date_created`, `modified`,
    `root`, `parent`, and `contributors`.  Most are string fields and will be filtered using simple substring matching.  `public`
    is a boolean, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true`
    or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """
    view_category = 'registrations'
    view_name = 'registration-children'
    serializer_class = RegistrationSerializer

    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    ordering = ('-modified',)

    def get_default_queryset(self):
        return default_node_list_permission_queryset(user=self.request.user, model_cls=Registration)

    def get_queryset(self):
        registration = self.get_node()
        registration_pks = registration.node_relations.filter(is_node_link=False).select_related('child').values_list('child__pk', flat=True)
        return self.get_queryset_from_request().filter(pk__in=registration_pks).can_view(self.request.user).order_by('-modified')


class RegistrationCitationDetail(NodeCitationDetail, RegistrationMixin):
    """ The registration citation for a registration in CSL format *read only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##RegistraitonCitationDetail Attributes

        name                     type                description
        =================================================================================
        id                       string               unique ID for the citation
        title                    string               title of project or component
        author                   list                 list of authors for the work
        publisher                string               publisher - most always 'GakuNin RDM'
        type                     string               type of citation - web
        doi                      string               doi of the resource

    """
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    view_category = 'registrations'
    view_name = 'registration-citation'


class RegistrationCitationStyleDetail(NodeCitationStyleDetail, RegistrationMixin):
    """ The registration citation for a registration in a specific style's format t *read only*

        ##Note
        **This API endpoint is under active development, and is subject to change in the future**

    ##RegistrationCitationStyleDetail Attributes

        name                     type                description
        =================================================================================
        citation                string               complete citation for a registration in the given style

    """
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    view_category = 'registrations'
    view_name = 'registration-style-citation'


class RegistrationForksList(NodeForksList, RegistrationMixin):
    """Forks of the current registration. *Writeable*.

    Paginated list of the current node's forks ordered by their `forked_date`. Forks are copies of projects that you can
    change without affecting the original project.  When creating a fork, your fork will will only contain public components or those
    for which you are a contributor.  Private components that you do not have access to will not be forked.

    ##Node Fork Attributes

    <!--- Copied Attributes from NodeDetail with exception of forked_date-->

    OSF Node Fork entities have the "nodes" `type`.

        name                        type               description
        ===============================================================================================================================
        title                       string             title of project or component
        description                 string             description of the node
        category                    string             node category, must be one of the allowed values
        date_created                iso8601 timestamp  timestamp that the node was created
        date_modified               iso8601 timestamp  timestamp when the node was last updated
        tags                        array of strings   list of tags that describe the node
        registration                boolean            has this project been registered? (always False)
        collection                  boolean            is this node a collection (always False)
        fork                        boolean            is this node a fork of another node? (always True)
        public                      boolean            has this node been made publicly-visible?
        forked_date                 iso8601 timestamp  timestamp when the node was forked
        current_user_can_comment    boolean            Whether the current user is allowed to post comments
        current_user_permissions    array of strings   List of strings representing the permissions for the current user on this node

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Create Node Fork

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON): {
                         "data": {
                           "type": "nodes", # required
                           "attributes": {
                             "title": {title} # optional
                           }
                         }
                    }
        Success: 201 CREATED + node representation

    To create a fork of the current node, issue a POST request to this endpoint.  The `title` field is optional, with the
    default title being 'Fork of ' + the current node's title. If the fork's creation is successful the API will return a
    201 response with the representation of the forked node in the body. For the new fork's canonical URL, see the `/links/self`
    field of the response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, `tags`, `date_created`,
    `modified`, `root`, `parent`, and `contributors`. Most are string fields and will be filtered using simple
    substring matching.  Others are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.
    Note that quoting `true` or `false` in the query will cause the match to fail regardless. `tags` is an array of simple strings.

    #This Request/Response
    """
    view_category = 'registrations'
    view_name = 'registration-forks'

class RegistrationCommentsList(NodeCommentsList, RegistrationMixin):
    """List of comments for a registration."""
    serializer_class = RegistrationCommentSerializer
    view_category = 'registrations'
    view_name = 'registration-comments'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        else:
            return RegistrationCommentSerializer


class RegistrationLogList(NodeLogList, RegistrationMixin):
    """List of logs for a registration."""
    view_category = 'registrations'
    view_name = 'registration-logs'


class RegistrationProvidersList(NodeProvidersList, RegistrationMixin):
    """List of providers for a registration."""
    serializer_class = RegistrationProviderSerializer

    view_category = 'registrations'
    view_name = 'registration-providers'


class RegistrationNodeLinksList(BaseNodeLinksList, RegistrationMixin):
    """Node Links to other nodes. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Node Link Attributes
    `type` is "node_links"

        None

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Relationships

    ### Target Node

    This endpoint shows the target node detail and is automatically embedded.

    ##Actions

    ###Adding Node Links
        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON): {
                       "data": {
                          "type": "node_links",                  # required
                          "relationships": {
                            "nodes": {
                              "data": {
                                "type": "nodes",                 # required
                                "id": "{target_node_id}",        # required
                              }
                            }
                          }
                       }
                    }
        Success:       201 CREATED + node link representation

    To add a node link (a pointer to another node), issue a POST request to this endpoint.  This effectively creates a
    relationship between the node and the target node.  The target node must be described as a relationship object with
    a "data" member, containing the nodes `type` and the target node `id`.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    #This Request/Response
    """
    view_category = 'registrations'
    view_name = 'registration-pointers'
    serializer_class = RegistrationNodeLinksSerializer
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    # TODO: This class doesn't exist
    # model_class = Pointer


class RegistrationNodeLinksDetail(BaseNodeLinksDetail, RegistrationMixin):
    """Node Link details. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Attributes
    `type` is "node_links"

        None

    ##Links

    *None*

    ##Relationships

    ###Target node

    This endpoint shows the target node detail and is automatically embedded.

    ##Actions

    ###Remove Node Link

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Success:       204 No Content

    To remove a node link from a node, issue a DELETE request to the `self` link.  This request will remove the
    relationship between the node and the target node, not the nodes themselves.

    ##Query Params

    *None*.

    #This Request/Response
    """
    view_category = 'registrations'
    view_name = 'registration-pointer-detail'
    serializer_class = RegistrationNodeLinksSerializer

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    # TODO: this class doesn't exist
    # model_class = Pointer

    # overrides RetrieveAPIView
    def get_object(self):
        registration = self.get_node()
        if not registration.is_registration:
            raise ValidationError('This is not a registration.')
        return registration


class RegistrationRegistrationsList(NodeRegistrationsList, RegistrationMixin):
    """List of registrations of a registration."""
    view_category = 'registrations'
    view_name = 'registration-registrations'


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    """List of files for a registration."""
    view_category = 'registrations'
    view_name = 'registration-files'
    serializer_class = RegistrationFileSerializer


class RegistrationFileDetail(NodeFileDetail, RegistrationMixin):
    """Detail of a file for a registration."""
    view_category = 'registrations'
    view_name = 'registration-file-detail'
    serializer_class = RegistrationFileSerializer


class RegistrationInstitutionsList(NodeInstitutionsList, RegistrationMixin):
    """List of the Institutions for a registration."""
    view_category = 'registrations'
    view_name = 'registration-institutions'


class RegistrationWikiList(NodeWikiList, RegistrationMixin):
    """List of wikis for a registration."""
    view_category = 'registrations'
    view_name = 'registration-wikis'

    serializer_class = RegistrationWikiSerializer


class RegistrationLinkedNodesList(LinkedNodesList, RegistrationMixin):
    """List of linked nodes for a registration."""
    view_category = 'registrations'
    view_name = 'linked-nodes'


class RegistrationLinkedNodesRelationship(JSONAPIBaseView, generics.RetrieveAPIView, RegistrationMixin):
    """ Relationship Endpoint for Nodes -> Linked Node relationships

    Used to retrieve the ids of the linked nodes attached to this collection. For each id, there
    exists a node link that contains that node.

    ##Actions

    """
    view_category = 'registrations'
    view_name = 'node-pointer-relationship'

    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = LinkedNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    def get_object(self):
        node = self.get_node(check_object_permissions=False)
        auth = get_user_auth(self.request)
        obj = {'data': [
            linked_node for linked_node in
            node.linked_nodes.filter(is_deleted=False).exclude(type='osf.collection').exclude(type='osf.registration')
            if linked_node.can_view(auth)
        ], 'self': node}
        self.check_object_permissions(self.request, obj)
        return obj


class RegistrationLinkedRegistrationsRelationship(JSONAPIBaseView, generics.RetrieveAPIView, RegistrationMixin):
    """Relationship Endpoint for Registration -> Linked Registration relationships. *Read-only*

    Used to retrieve the ids of the linked registrations attached to this collection. For each id, there
    exists a node link that contains that registration.
    """

    view_category = 'registrations'
    view_name = 'node-registration-pointer-relationship'

    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = LinkedRegistrationsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON,)

    def get_object(self):
        node = self.get_node(check_object_permissions=False)
        auth = get_user_auth(self.request)
        obj = {
            'data': [
                linked_registration for linked_registration in
                node.linked_nodes.filter(is_deleted=False, type='osf.registration').exclude(type='osf.collection')
                if linked_registration.can_view(auth)
            ],
            'self': node
        }
        self.check_object_permissions(self.request, obj)
        return obj


class RegistrationLinkedRegistrationsList(NodeLinkedRegistrationsList, RegistrationMixin):
    """List of registrations linked to this registration. *Read-only*.

    Linked registrations are the registration nodes pointed to by node links.

    <!--- Copied Spiel from RegistrationDetail -->
    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registration's detail view are not necessary. A withdrawn registration will display a limited subset of information,
    namely, title, description, created, registration, withdrawn, date_registered, withdrawal_justification, and
    registration supplement. All other fields will be displayed as null. Additionally, the only relationships permitted
    to be accessed for a withdrawn registration are the contributors - other relationships will return a 403.

    ##Linked Registration Attributes

    <!--- Copied Attributes from RegistrationDetail -->

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, or `tags`.  `title`,
    `description`, and `category` are string fields and will be filtered using simple substring matching.  `public` and
    `registration` are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note
    that quoting `true` or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response
    """

    serializer_class = RegistrationSerializer
    view_category = 'registrations'
    view_name = 'linked-registrations'


class RegistrationViewOnlyLinksList(NodeViewOnlyLinksList, RegistrationMixin):

    required_read_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_WRITE]

    view_category = 'registrations'
    view_name = 'registration-view-only-links'


class RegistrationViewOnlyLinkDetail(NodeViewOnlyLinkDetail, RegistrationMixin):

    required_read_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_WRITE]

    view_category = 'registrations'
    view_name = 'registration-view-only-link-detail'


class RegistrationIdentifierList(RegistrationMixin, NodeIdentifierList):
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

    serializer_class = RegistrationIdentifierSerializer
