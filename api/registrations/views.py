from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from framework.auth.oauth_scopes import CoreScopes

from osf.models import AbstractNode, Registration, OSFUser, RegistrationProvider
from osf.utils.permissions import WRITE_NODE
from api.base import permissions as base_permissions
from api.base import generic_bulk_views as bulk_views
from api.base.filters import ListFilterMixin
from api.base.views import (
    JSONAPIBaseView,
    BaseChildrenList,
    BaseContributorDetail,
    BaseContributorList,
    BaseNodeLinksDetail,
    BaseNodeLinksList,
    WaterButlerMixin,
)
from api.base.serializers import HideIfWithdrawal, LinkedRegistrationsRelationshipSerializer
from api.base.serializers import LinkedNodesRelationshipSerializer
from api.base.pagination import NodeContributorPagination
from api.base.exceptions import Conflict
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIMultipleRelationshipsParser
from api.base.parsers import JSONAPIRelationshipParserForRegularJSON, JSONAPIMultipleRelationshipsParserForRegularJSON
from api.base.utils import (
    get_user_auth,
    default_node_list_permission_queryset,
    is_bulk_request,
    is_truthy,
)
from api.comments.serializers import RegistrationCommentSerializer, CommentCreateSerializer
from api.draft_registrations.views import DraftMixin
from api.identifiers.serializers import RegistrationIdentifierSerializer
from api.nodes.views import NodeIdentifierList, NodeBibliographicContributorsList, NodeSubjectsList, NodeSubjectsRelationship
from api.users.views import UserMixin
from api.users.serializers import UserSerializer

from api.nodes.permissions import (
    ReadOnlyIfRegistration,
    ContributorDetailPermissions,
    ContributorOrPublic,
    ContributorOrPublicForRelationshipPointers,
    AdminOrPublic,
    ExcludeWithdrawals,
    NodeLinksShowIfVersion,
)
from api.registrations.permissions import ContributorOrModerator
from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationContributorsSerializer,
    RegistrationCreateSerializer,
    RegistrationStorageProviderSerializer,
)

from api.nodes.filters import NodesFilterMixin

from api.nodes.views import (
    NodeMixin, NodeRegistrationsList, NodeLogList,
    NodeCommentsList, NodeStorageProvidersList, NodeFilesList, NodeFileDetail,
    NodeInstitutionsList, NodeForksList, NodeWikiList, LinkedNodesList,
    NodeViewOnlyLinksList, NodeViewOnlyLinkDetail, NodeCitationDetail, NodeCitationStyleDetail,
    NodeLinkedRegistrationsList, NodeLinkedByNodesList, NodeLinkedByRegistrationsList, NodeInstitutionsRelationship,
)

from api.registrations.serializers import RegistrationNodeLinksSerializer, RegistrationFileSerializer
from api.wikis.serializers import RegistrationWikiSerializer

from api.base.utils import get_object_or_error
from api.actions.serializers import RegistrationActionSerializer
from api.requests.serializers import RegistrationRequestSerializer
from framework.sentry import log_exception
from osf.utils.permissions import ADMIN
from api.providers.permissions import MustBeModerator
from api.providers.views import ProviderMixin


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
            display_name='node',

        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection or not node.is_registration:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class RegistrationList(JSONAPIBaseView, generics.ListCreateAPIView, bulk_views.BulkUpdateJSONAPIView, NodesFilterMixin, DraftMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_list).
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

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    # overrides BulkUpdateJSONAPIView
    def get_serializer_class(self):
        """
        Use RegistrationDetailSerializer which requires 'id'
        """
        if self.request.method in ('PUT', 'PATCH'):
            return RegistrationDetailSerializer
        elif self.request.method == 'POST':
            return RegistrationCreateSerializer
        else:
            return RegistrationSerializer

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        return default_node_list_permission_queryset(user=self.request.user, model_cls=Registration)

    def is_blacklisted(self):
        query_params = self.parse_query_params(self.request.query_params)
        for key, field_names in query_params.items():
            for field_name, data in field_names.items():
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
                return Registration.objects.get_nodes_for_user(auth.user, WRITE_NODE, registrations)

            for registration in registrations:
                if not registration.can_edit(auth):
                    raise PermissionDenied
            return registrations

        blacklisted = self.is_blacklisted()
        registrations = self.get_queryset_from_request()
        # If attempting to filter on a blacklisted field, exclude withdrawals.
        if blacklisted:
            registrations = registrations.exclude(retraction__isnull=False)

        return registrations.select_related(
            'root',
            'root__embargo',
            'root__embargo_termination_approval',
            'root__retraction',
            'root__registration_approval',
        )

    # overrides ListCreateJSONAPIView
    def perform_create(self, serializer):
        """Create a registration from a draft.
        """
        draft_id = self.request.data.get('draft_registration', None) or self.request.data.get('draft_registration_id', None)
        draft = self.get_draft(draft_id)
        node = draft.branched_from
        user = get_user_auth(self.request).user

        # A user must be an admin contributor on the node (not group member), and have
        # admin perms on the draft to register
        if node.is_admin_contributor(user) and draft.has_permission(user, ADMIN):
            try:
                serializer.save(draft=draft)
            except ValidationError as e:
                log_exception()
                raise e
        else:
            raise PermissionDenied(
                'You must be an admin contributor on both the project and the draft registration to create a registration.',
            )

    def check_branched_from(self, draft):
        # Overrides DraftMixin - no node_id in kwargs
        return


class RegistrationDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, RegistrationMixin, WaterButlerMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationDetailSerializer
    view_category = 'registrations'
    view_name = 'registration-detail'

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    # overrides RetrieveAPIView
    def get_object(self):
        registration = self.get_node()
        if not registration.is_registration:
            raise ValidationError('This is not a registration.')
        return registration

    def get_renderer_context(self):
        context = super(RegistrationDetail, self).get_renderer_context()
        show_counts = is_truthy(self.request.query_params.get('related_counts', False))
        if show_counts:
            registration = self.get_object()
            context['meta'] = {
                'templated_by_count': registration.templated_list.count(),
            }
        return context


class RegistrationContributorsList(BaseContributorList, RegistrationMixin, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_contributors_list).
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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_contributors_read).
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


class RegistrationBibliographicContributorsList(NodeBibliographicContributorsList, RegistrationMixin):

    pagination_class = NodeContributorPagination
    serializer_class = RegistrationContributorsSerializer

    view_category = 'registrations'
    view_name = 'registration-bibliographic-contributors'


class RegistrationImplicitContributorsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, RegistrationMixin):
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = OSFUser

    serializer_class = UserSerializer
    view_category = 'registrations'
    view_name = 'registration-implicit-contributors'
    ordering = ('_order',)  # default ordering

    def get_default_queryset(self):
        node = self.get_node()

        return node.parent_admin_contributors

    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        return queryset


class RegistrationChildrenList(BaseChildrenList, generics.ListAPIView, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_children_list).
    """
    view_category = 'registrations'
    view_name = 'registration-children'
    serializer_class = RegistrationSerializer

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = Registration


class RegistrationCitationDetail(NodeCitationDetail, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_citations_list).
    """
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    view_category = 'registrations'
    view_name = 'registration-citation'


class RegistrationCitationStyleDetail(NodeCitationStyleDetail, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_citation_read).
    """
    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    view_category = 'registrations'
    view_name = 'registration-style-citation'


class RegistrationForksList(NodeForksList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_forks_list).
    """
    view_category = 'registrations'
    view_name = 'registration-forks'

class RegistrationCommentsList(NodeCommentsList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_comments_list).
    """
    serializer_class = RegistrationCommentSerializer
    view_category = 'registrations'
    view_name = 'registration-comments'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        else:
            return RegistrationCommentSerializer


class RegistrationLogList(NodeLogList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_logs_list).
    """
    view_category = 'registrations'
    view_name = 'registration-logs'


class RegistrationStorageProvidersList(NodeStorageProvidersList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_providers_list).
    """
    serializer_class = RegistrationStorageProviderSerializer

    view_category = 'registrations'
    view_name = 'registration-storage-providers'


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


class RegistrationLinkedByNodesList(NodeLinkedByNodesList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-linked-by-nodes'


class RegistrationLinkedByRegistrationsList(NodeLinkedByRegistrationsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-linked-by-registrations'


class RegistrationRegistrationsList(NodeRegistrationsList, RegistrationMixin):
    """List of registrations of a registration."""
    view_category = 'registrations'
    view_name = 'registration-registrations'


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_files_list).
    """
    view_category = 'registrations'
    view_name = 'registration-files'
    serializer_class = RegistrationFileSerializer


class RegistrationFileDetail(NodeFileDetail, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_files_read).
    """
    view_category = 'registrations'
    view_name = 'registration-file-detail'
    serializer_class = RegistrationFileSerializer


class RegistrationInstitutionsList(NodeInstitutionsList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_institutions_list).
    """
    view_category = 'registrations'
    view_name = 'registration-institutions'


class RegistrationSubjectsList(NodeSubjectsList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_subjects_list).
    """
    view_category = 'registrations'
    view_name = 'registration-subjects'

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]


class RegistrationSubjectsRelationship(NodeSubjectsRelationship, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_subjects_relationship).
    """

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    view_category = 'registrations'
    view_name = 'registration-relationships-subjects'


class RegistrationInstitutionsRelationship(NodeInstitutionsRelationship, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_institutions_relationship).
    """
    view_category = 'registrations'
    view_name = 'registration-relationships-institutions'

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        AdminOrPublic,
    )


class RegistrationWikiList(NodeWikiList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_wikis_list).
    """
    view_category = 'registrations'
    view_name = 'registration-wikis'

    serializer_class = RegistrationWikiSerializer


class RegistrationLinkedNodesList(LinkedNodesList, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_linked_nodes_list).
    """
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
        obj = {
            'data': [
                linked_node for linked_node in
                node.linked_nodes.filter(is_deleted=False).exclude(type='osf.collection').exclude(type='osf.registration')
                if linked_node.can_view(auth)
            ], 'self': node,
        }
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
            'self': node,
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
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_view_only_links_list).
    """
    required_read_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_WRITE]

    view_category = 'registrations'
    view_name = 'registration-view-only-links'


class RegistrationViewOnlyLinkDetail(NodeViewOnlyLinkDetail, RegistrationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_view_only_links_read).
    """
    required_read_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.REGISTRATION_VIEW_ONLY_LINKS_WRITE]

    view_category = 'registrations'
    view_name = 'registration-view-only-link-detail'


class RegistrationIdentifierList(RegistrationMixin, NodeIdentifierList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/registrations_identifiers_list).
    """

    serializer_class = RegistrationIdentifierSerializer


class RegistrationActionList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView, ProviderMixin):
    provider_class = RegistrationProvider

    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        ContributorOrModerator,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]
    view_category = 'registrations'
    view_name = 'registration-actions-list'

    serializer_class = RegistrationActionSerializer
    ordering = ('-created',)
    node_lookup_url_kwarg = 'node_id'

    def get_registration(self):
        registration = get_object_or_error(
            Registration,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
            check_deleted=False,
        )
        # May raise a permission denied
        self.check_object_permissions(self.request, registration)
        return registration

    def get_default_queryset(self):
        return self.get_registration().actions.all()

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        if not target.provider.is_reviewed:
            raise Conflict(f'{target.provider.name } is an umoderated provider. If you believe this is an error, contact OSF Support.')

        serializer.save(user=self.request.user)


class RegistrationRequestList(JSONAPIBaseView, ListFilterMixin, generics.ListCreateAPIView, RegistrationMixin, ProviderMixin):
    provider_class = RegistrationProvider

    required_read_scopes = [CoreScopes.NODE_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )

    view_category = 'registrations'
    view_name = 'registration-requests-list'

    serializer_class = RegistrationRequestSerializer

    def get_default_queryset(self):
        return self.get_node().requests.all()

    def get_queryset(self):
        return self.get_queryset_from_request()
