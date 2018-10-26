import re

from django.apps import apps
from django.db.models import Q, OuterRef, Exists
from django.utils import timezone
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound, MethodNotAllowed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from addons.osfstorage.models import OsfStorageFolder
from api.addons.serializers import NodeAddonFolderSerializer
from api.addons.views import AddonSettingsMixin
from api.base import generic_bulk_views as bulk_views
from api.base import permissions as base_permissions
from api.base.exceptions import (
    InvalidModelValueError,
    JSONAPIException,
    Gone,
    InvalidFilterOperator,
    InvalidFilterValue,
    RelationshipPostMakesNoChanges,
    EndpointNotImplementedError,
)
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.pagination import CommentPagination, NodeContributorPagination, MaxSizePagination
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.settings import ADDONS_OAUTH, API_BASE
from api.base.throttling import (
    UserRateThrottle,
    NonCookieAuthThrottle,
    AddContributorThrottle,
)
from api.base.utils import default_node_list_queryset, default_node_list_permission_queryset
from api.base.utils import get_object_or_error, is_bulk_request, get_user_auth, is_truthy
from api.base.views import JSONAPIBaseView
from api.base.views import (
    BaseContributorDetail,
    BaseContributorList,
    BaseLinkedList,
    BaseNodeLinksDetail,
    BaseNodeLinksList,
    LinkedNodesRelationship,
    LinkedRegistrationsRelationship,
    WaterButlerMixin
)
from api.caching.tasks import ban_url
from api.citations.utils import render_citation
from api.comments.permissions import CanCommentOrPublic
from api.comments.serializers import (CommentCreateSerializer,
                                      NodeCommentSerializer)
from api.files.serializers import FileSerializer, OsfStorageFileSerializer
from api.identifiers.serializers import NodeIdentifierSerializer
from api.identifiers.views import IdentifierList
from api.institutions.serializers import InstitutionSerializer
from api.logs.serializers import NodeLogSerializer
from api.nodes.filters import NodesFilterMixin
from api.nodes.permissions import (
    IsAdmin,
    IsPublic,
    AdminOrPublic,
    ContributorOrPublic,
    RegistrationAndPermissionCheckForPointers,
    ContributorDetailPermissions,
    ReadOnlyIfRegistration,
    IsAdminOrReviewer,
    WriteOrPublicForRelationshipInstitutions,
    ExcludeWithdrawals,
    NodeLinksShowIfVersion,
)
from api.nodes.serializers import (
    NodeSerializer,
    ForwardNodeAddonSettingsSerializer,
    NodeAddonSettingsSerializer,
    NodeLinksSerializer,
    NodeForksSerializer,
    NodeDetailSerializer,
    NodeProviderSerializer,
    DraftRegistrationSerializer,
    DraftRegistrationDetailSerializer,
    NodeContributorsSerializer,
    NodeContributorDetailSerializer,
    NodeInstitutionsRelationshipSerializer,
    NodeContributorsCreateSerializer,
    NodeViewOnlyLinkSerializer,
    NodeViewOnlyLinkUpdateSerializer,
    NodeCitationSerializer,
    NodeCitationStyleSerializer
)
from api.preprints.serializers import PreprintSerializer
from api.registrations.serializers import RegistrationSerializer
from api.users.views import UserMixin
from api.wikis.serializers import NodeWikiSerializer
from framework.auth.oauth_scopes import CoreScopes
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from osf.models import AbstractNode
from osf.models import (Node, PrivateLink, Institution, Comment, DraftRegistration,)
from osf.models import OSFUser
from osf.models import NodeRelation, Guid
from osf.models import BaseFileNode
from osf.models.files import File, Folder
from addons.wiki.models import NodeWikiPage
from website import mails
from website.exceptions import NodeStateError
from website.util.permissions import ADMIN, PERMISSIONS
from osf.models import RdmTimestampGrantPattern

import logging
logger = logging.getLogger(__name__)

class NodeMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the node_id kwarg.
    """

    serializer_class = NodeSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = None

        if self.kwargs.get('is_embedded') is True:
            # If this is an embedded request, the node might be cached somewhere
            node = self.request.parents[Node].get(self.kwargs[self.node_lookup_url_kwarg])

        try:
            timestamp_pattern = RdmTimestampGrantPattern.objects.get(node_guid=self.kwargs['node_id'])
            timestamp_pattern.timestamp_pattern_division = int(self.request.data['timestampPattern'])
            timestamp_pattern.save()
        except Exception:
            pass
        if node is None:
            node = get_object_or_error(
                Node,
                self.kwargs[self.node_lookup_url_kwarg],
                self.request,
                display_name='node'
            )

        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection or node.is_registration:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class DraftMixin(object):

    serializer_class = DraftRegistrationSerializer

    def get_draft(self, draft_id=None):
        node_id = self.kwargs['node_id']
        if draft_id is None:
            draft_id = self.kwargs['draft_id']
        draft = get_object_or_error(DraftRegistration, draft_id, self.request)

        if not draft.branched_from._id == node_id:
            raise ValidationError('This draft registration is not created from the given node.')

        if self.request.method not in drf_permissions.SAFE_METHODS:
            registered_and_deleted = draft.registered_node and draft.registered_node.is_deleted

            if draft.registered_node and not draft.registered_node.is_deleted:
                raise PermissionDenied('This draft has already been registered and cannot be modified.')

            if draft.is_pending_review:
                raise PermissionDenied('This draft is pending review and cannot be modified.')

            if draft.requires_approval and draft.is_approved and (not registered_and_deleted):
                raise PermissionDenied('This draft has already been approved and cannot be modified.')

        self.check_object_permissions(self.request, draft.branched_from)
        return draft


class NodeList(JSONAPIBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodesFilterMixin, WaterButlerMixin):
    """Nodes that represent projects and components. *Writeable*.

    Paginated list of nodes ordered by their `modified`.  Each resource contains the full representation of the
    node, meaning additional requests to an individual node's detail view are not necessary.  Registrations and withdrawn
    registrations cannot be accessed through this endpoint (see registration endpoints instead).

    <!--- Copied Spiel from NodeDetail -->

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a [category
    field](/v2/#osf-node-categories) that includes 'project' as an option. The categorization essentially determines
    which icon is displayed by the node in the front-end UI and helps with search organization. Top-level nodes may have
    a category other than project, and children nodes may have a category of project.

    ##Node Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name                            type               description
        =================================================================================
        title                           string             title of project or component
        description                     string             description of the node
        category                        string             node category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        registration                    boolean            is this a registration? (always false - may be deprecated in future versions)
        fork                            boolean            is this node a fork of another node?
        public                          boolean            has this node been made publicly-visible?
        preprint                        boolean            is this a preprint?
        collection                      boolean            is this a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
            year                        string             date range of the license
            copyright_holders           array of strings   holders of the applied license

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Creating New Nodes

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "nodes", # required
                           "attributes": {
                             "title":         {title},          # required
                             "category":      {category},       # required
                             "description":   {description},    # optional
                             "tags":          [{tag1}, {tag2}], # optional
                             "public":        true|false        # optional
                             "template_from": {node_id}         # optional
                           }
                         }
                       }
        Success:       201 CREATED + node representation

    New nodes are created by issuing a POST request to this endpoint.  The `title` and `category` fields are
    mandatory. `category` must be one of the [permitted node categories](/v2/#osf-node-categories).  `public` defaults
    to false.  All other fields not listed above will be ignored.  If the node creation is successful the API will
    return a 201 response with the representation of the new node in the body.  For the new node's canonical URL, see
    the `/links/self` field of the response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    + `view_only=<Str>` -- Allow users with limited access keys to access this node. Note that some keys are anonymous,
    so using the view_only key will cause user-related information to no longer serialize. This includes blank ids for
    users and contributors and missing serializer fields and relationships.

    Nodes may be filtered by their `id`, `title`, `category`, `description`, `public`, `tags`, `date_created`, `date_modified`,
    `root`, `parent`, 'preprint', and `contributors`.  Most are string fields and will be filtered using simple substring matching.  `public`
    and `preprint` are boolean values, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true`
    or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    model_class = apps.get_model('osf.AbstractNode')

    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'node-list'

    ordering = ('-modified', )  # default ordering

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        return default_node_list_permission_queryset(user=self.request.user, model_cls=Node)

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        # For bulk requests, queryset is formed from request body.
        if is_bulk_request(self.request):
            auth = get_user_auth(self.request)
            nodes = Node.objects.filter(guids___id__in=[node['id'] for node in self.request.data])

            # If skip_uneditable=True in query_params, skip nodes for which the user
            # does not have EDIT permissions.
            if is_truthy(self.request.query_params.get('skip_uneditable', False)):
                has_permission = nodes.filter(contributor__user_id=auth.user.id, contributor__write=True).values_list('guids___id', flat=True)
                return Node.objects.filter(guids___id__in=has_permission)

            for node in nodes:
                if not node.can_edit(auth):
                    raise PermissionDenied

            return nodes
        else:
            return self.get_queryset_from_request()

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView, BulkDestroyJSONAPIView
    def get_serializer_class(self):
        """
        Use NodeDetailSerializer which requires 'id'
        """
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return NodeDetailSerializer
        else:
            return NodeSerializer

    # overrides ListBulkCreateJSONAPIView
    def perform_create(self, serializer):
        """Create a node.

        :param serializer:
        """
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)

    # overrides BulkDestroyJSONAPIView
    def allow_bulk_destroy_resources(self, user, resource_list):
        """User must have admin permissions to delete nodes."""
        if is_truthy(self.request.query_params.get('skip_uneditable', False)):
            return any([node.has_permission(user, ADMIN) for node in resource_list])
        return all([node.has_permission(user, ADMIN) for node in resource_list])

    def bulk_destroy_skip_uneditable(self, resource_object_list, user, object_type):
        """
        If skip_uneditable=True in query_params, skip the resources for which the user does not have
        admin permissions and delete the remaining resources
        """
        allowed = []
        skipped = []

        if not is_truthy(self.request.query_params.get('skip_uneditable', False)):
            return None

        for resource in resource_object_list:
            if resource.has_permission(user, ADMIN):
                allowed.append(resource)
            else:
                skipped.append({'id': resource._id, 'type': object_type})

        return {'skipped': skipped, 'allowed': allowed}

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        try:
            instance.remove_node(auth=auth)
        except NodeStateError as err:
            raise ValidationError(err.message)
        instance.save()


class NodeDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, NodeMixin, WaterButlerMixin):
    """Details about a given node (project or component). *Writeable*.

    A registration or withdrawn registration cannot be accessed through this endpoint. See Registration Detail endpoint.

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a [category
    field](/v2/#osf-node-categories) that includes 'project' as an option. The categorization essentially determines
    which icon is displayed by the node in the front-end UI and helps with search organization. Top-level nodes may have
    a category other than project, and children nodes may have a category of project.

    ###Permissions

    Nodes that are made public will give read-only access to everyone. Private nodes require explicit read
    permission. Write and admin access are the same for public and private nodes. Administrators on a parent node have
    implicit read permissions for all child nodes.

    ##Attributes

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
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license

    ##Relationships

    ###Children

    List of nodes that are children of this node.  New child nodes may be added through this endpoint.

    ###Comments

    List of comments on this node.  New comments can be left on the node through this endpoint.

    ###Contributors

    List of users who are contributors to this node. Contributors may have "read", "write", or "admin" permissions.
    A node must always have at least one "admin" contributor.  Contributors may be added via this endpoint.

    ###Draft Registrations

    List of draft registrations of the current node.

    ###Files

    List of top-level folders (actually cloud-storage providers) associated with this node. This is the starting point
    for accessing the actual files stored within this node.

    ###Forked From

    If this node was forked from another node, the canonical endpoint of the node that was forked from will be
    available in the `/forked_from/links/related/href` key.  Otherwise, it will be null.

    ###Logs

    List of read-only log actions pertaining to the node.

    ###Node Links

    List of links (pointers) to other nodes on the OSF.  Node links can be added through this endpoint.

    ###Parent

    If this node is a child node of another node, the parent's canonical endpoint will be available in the
    `/parent/links/related/href` key.  Otherwise, it will be null.

    ###Registrations

    List of registrations of the current node.

    ###Root

    Returns the top-level node associated with the current node.  If the current node is the top-level node, the root is
    the current node.

    ### Linked Nodes

    List of nodes linked to the current node.

    ### Linked Registrations

    List of registrations linked to the current node.

    ##Links

        self:  the canonical api endpoint of this node
        html:  this node's page on the OSF website

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "nodes",   # required
                           "id":   {node_id}, # required
                           "attributes": {
                             "title":       {title},          # mandatory
                             "category":    {category},       # mandatory
                             "description": {description},    # optional
                             "tags":        [{tag1}, {tag2}], # optional
                             "public":      true|false        # optional
                           }
                         }
                       }
        Success:       200 OK + node representation

    To update a node, issue either a PUT or a PATCH request against the `/links/self` URL.  The `title` and `category`
    fields are mandatory if you PUT and optional if you PATCH.  The `tags` parameter must be an array of strings.
    Non-string values will be accepted and stringified, but we make no promises about the stringification output.  So
    don't do that.

    ###Delete

        Method:   DELETE
        URL:      /links/self
        Params:   <none>
        Success:  204 No Content

    To delete a node, issue a DELETE request against `/links/self`.  A successful delete will return a 204 No Content
    response. Attempting to delete a node you do not own will result in a 403 Forbidden.

    ##Query Params

    + `view_only=<Str>` -- Allow users with limited access keys to access this node. Note that some keys are anonymous, so using the view_only key will cause user-related information to no longer serialize. This includes blank ids for users and contributors and missing serializer fields and relationships.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = NodeDetailSerializer
    view_category = 'nodes'
    view_name = 'node-detail'

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


class NodeContributorsList(BaseContributorList, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodeMixin):
    """Contributors (users) for a node.

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
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]
    model_class = OSFUser

    throttle_classes = (AddContributorThrottle, UserRateThrottle, NonCookieAuthThrottle, )

    pagination_class = NodeContributorPagination
    serializer_class = NodeContributorsSerializer
    view_category = 'nodes'
    view_name = 'node-contributors'
    ordering = ('_order',)  # default ordering

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'bibliographic':
            operation['source_field_name'] = 'visible'

    def build_query_from_field(self, field_name, operation):
        if field_name == 'permission':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            # operation['value'] should be 'admin', 'write', or 'read'
            if operation['value'].lower().strip() not in PERMISSIONS:
                raise InvalidFilterValue(value=operation['value'])
            return Q(**{operation['value'].lower().strip(): True})
        return super(NodeContributorsList, self).build_query_from_field(field_name, operation)

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

    # overrides ListBulkCreateJSON APIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        # If bulk request, queryset only contains contributors in request
        if is_bulk_request(self.request):
            contrib_ids = []
            for item in self.request.data:
                try:
                    contrib_ids.append(item['id'].split('-')[1])
                except AttributeError:
                    raise ValidationError('Contributor identifier not provided.')
                except IndexError:
                    raise ValidationError('Contributor identifier incorrectly formatted.')
            queryset = queryset.filter(user__guids___id__in=contrib_ids)
        return queryset

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_node()
        if len(node.visible_contributors) == 1 and node.get_visible(instance):
            raise ValidationError('Must have at least one visible contributor')
        if not node.contributor_set.filter(user=instance).exists():
            raise NotFound('User cannot be found in the list of contributors.')
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError('Must have at least one registered admin contributor')

    # Overrides BulkDestroyJSONAPIView
    def get_requested_resources(self, request, request_data):
        requested_ids = []
        for data in request_data:
            try:
                requested_ids.append(data['id'].split('-')[1])
            except IndexError:
                raise ValidationError('Contributor identifier incorrectly formatted.')

        resource_object_list = OSFUser.objects.filter(guids___id__in=requested_ids)
        for resource in resource_object_list:
            if getattr(resource, 'is_deleted', None):
                raise Gone

        if len(resource_object_list) != len(request_data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        return resource_object_list


class NodeContributorDetail(BaseContributorDetail, generics.RetrieveUpdateDestroyAPIView, NodeMixin, UserMixin):
    """Detail of a contributor for a node. *Writeable*.

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
        index                       integer  The position in the list of contributors reflected in the bibliography. Zero Indexed.

    ##Relationships

    ###Users

    This endpoint shows the contributor user detail.

    ##Links

        self:           the canonical api endpoint of this contributor
        html:           the contributing user's page on the OSF website
        profile_image:  a url to the contributing user's profile image

    ##Actions

    ###Update Contributor

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "contributors",                    # required
                           "id": {contributor_id},                    # required
                           "attributes": {
                             "bibliographic": true|false,             # optional
                             "permission": "read"|"write"|"admin"     # optional
                             "index": "0"                             # optional
                           }
                         }
                       }
        Success:       200 OK + node representation

    To update a contributor's bibliographic preferences, order in the bibliography,
    or access permissions for the node, issue a PUT request to the
    `self` link. Since this endpoint has no mandatory attributes, PUT and PATCH are functionally the same.  If the given
    user is not already in the contributor list, a 404 Not Found error will be returned.  A node must always have at
    least one admin, and any attempt to downgrade the permissions of a sole admin will result in a 400 Bad Request
    error.

    ###Remove Contributor

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Success:       204 No Content

    To remove a contributor from a node, issue a DELETE request to the `self` link.  Attempting to remove the only admin
    from a node will result in a 400 Bad Request response.  This request will only remove the relationship between the
    node and the user, not the user itself.

    ##Query Params

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` so that it points the image scaled to the given
    size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response

    """
    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]

    serializer_class = NodeContributorDetailSerializer
    view_category = 'nodes'
    view_name = 'node-contributor-detail'

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        node = self.get_node()
        auth = get_user_auth(self.request)
        if len(node.visible_contributors) == 1 and instance.visible:
            raise ValidationError('Must have at least one visible contributor')
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError('Must have at least one registered admin contributor')


class NodeDraftRegistrationsList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin):
    """Draft registrations of the current node.

     <!--- Copied partially from NodeDraftRegistrationDetail -->

    Draft registrations contain the supplemental registration questions that accompany a registration. A registration
    is a frozen version of the project that can never be edited or deleted but can be withdrawn.
    Your original project remains editable but will now have the registration linked to it.

    ###Permissions

    Users must have admin permission on the node in order to view or create a draft registration.

    ##Draft Registration Attributes


    Draft Registrations have the "draft_registrations" `type`.

        name                       type               description
        ===========================================================================
        registration_supplement    string             id of registration_schema, must be an active schema
        registration_metadata      dictionary         dictionary of question ids and responses from registration schema
        datetime_initiated         iso8601 timestamp  timestamp that the draft was created
        datetime_updated           iso8601 timestamp  timestamp when the draft was last updated

    ##Relationships

    ###Branched From

    Node that the draft is branched from.  The node endpoint is available in `/branched_from/links/related/href`.

    ###Initiator

    User who initiated the draft registration.  The user endpoint is available in `/initiator/links/related/href`.

    ##Registration Schema

    Detailed registration schema.  The schema endpoint is available in `/registration_schema/links/related/href`.

    ##Actions

    ###Create Draft Registration

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "type": "draft_registrations",  # required
                            "attributes": {
                                "registration_supplement": {schema_id}, # required
                                "registration_metadata": {"question_id": {"value": "question response"}} # optional
                            }
                        }
                    }
        Success:       201 OK + draft representation

    To create a draft registration, issue a POST request to the `self` link.  Registration supplement must be the id of an
    active registration schema.  Registration metadata is not required on the creation of the draft. If registration metadata is included,
    it must be a dictionary with keys as question ids in the registration supplement, and values as nested dictionaries
    matching the specific format in the registration schema.  See registration schema endpoints for specifics. If question
    is multiple-choice, question response must exactly match one of the possible choices.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This request/response

    """
    permission_classes = (
        IsAdmin,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationSerializer
    view_category = 'nodes'
    view_name = 'node-draft-registrations'

    ordering = ('-modified',)

    # overrides ListCreateAPIView
    def get_queryset(self):
        node = self.get_node()
        return DraftRegistration.objects.filter(
            Q(registered_node=None) |
            Q(registered_node__is_deleted=True),
            branched_from=node,
            deleted__isnull=True
        )

    # overrides ListBulkCreateJSONAPIView
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(initiator=user, node=self.get_node())


class NodeDraftRegistrationDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, DraftMixin):
    """Details about a given draft registration. *Writeable*.

    Draft registrations contain the supplemental registration questions that accompany a registration. A registration
    is a frozen version of the project that can never be edited or deleted but can be withdrawn.  Answer the questions
    in the draft registration with PUT/PATCH requests until you are ready to submit.  Final submission will include sending the
    draft registration id as part of a POST request to the Node Registrations endpoint.

    ###Permissions

    Users must have admin permission on the node in order to view, update, or delete a draft registration.

    ##Attributes

    Draft Registrations have the "draft_registrations" `type`.

        name                       type               description
        ===========================================================================
        registration_supplement    string             id of registration_schema, must be an active schema
        registration_metadata      dictionary         dictionary of question ids and responses from registration schema
        datetime_initiated         iso8601 timestamp  timestamp that the draft was created
        datetime_updated           iso8601 timestamp  timestamp when the draft was last updated

    ##Relationships

    ###Branched From

    Node that the draft is branched from.  The node endpoint is available in `/branched_from/links/related/href`.

    ###Initiator

    User who initiated the draft registration.  The user endpoint is available in `/initiator/links/related/href`.

    ##Registration Schema

    Detailed registration schema.  The schema endpoint is available in `/registration_schema/links/related/href`.

    ##Actions

    ###Update Draft Registration

        Method:        PUT/PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "id": {draft_registration_id},  # required
                            "type": "draft_registrations",  # required
                            "attributes": {
                                "registration_metadata": {"question_id": {"value": "question response"}} # optional
                            }
                        }
                    }
        Success:       200 OK + draft representation

    To update a draft registration, issue a PUT/PATCH request to the `self` link.  Registration supplement cannot be updated
    after the draft registration has been created.  Registration metadata is required.  It must be a dictionary with
    keys as question ids in the registration form, and values as nested dictionaries matching the specific format in the
    registration schema. See registration schema endpoints for specifics. If question is multiple-choice, question response
    must exactly match one of the possible choices.


    ###Delete Draft Registration

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Success:       204 No Content

    To delete a draft registration, issue a DELETE request to the `self` link.  This request will remove the draft completely.
    A draft that has already been registered cannot be deleted.

    ##Query Params

    + `view_only=<Str>` -- Allow users with limited access keys to access this node. Note that some keys are anonymous,
    so using the view_only key will cause user-related information to no longer serialize. This includes blank ids for users and contributors and missing serializer fields and relationships.

    #This Request/Response

    """
    permission_classes = (
        IsAdminOrReviewer,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationDetailSerializer
    view_category = 'nodes'
    view_name = 'node-draft-registration-detail'

    def get_object(self):
        return self.get_draft()

    def perform_destroy(self, draft):
        draft.deleted = timezone.now()
        draft.save(update_fields=['deleted'])


class NodeRegistrationsList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin, DraftMixin):
    """Registrations of the current node.

    Registrations are read-only snapshots of a project that can never be edited or deleted but can be withdrawn. This view
    is a list of all the registrations and withdrawn registrations of the current node. To create a registration, first
    create a draft registration and answer the required supplemental registration questions. Then, submit a POST request
    to this endpoint with the draft registration id in the body of the request.

    <!--- Copied from RegistrationList -->

    A withdrawn registration will display a limited subset of information, namely, title, description,
    created, registration, withdrawn, date_registered, withdrawal_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a withdrawn
    registration are the contributors - other relationships will return a 403. Each resource contains the full representation
    of the registration, meaning additional requests to an individual registrations's detail view are not necessary.


    <!--- Copied Attributes from RegistrationList -->

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
        registration                    boolean            is this node a registration? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
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

    ###Create Registration

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "type": "registrations",                                         # required
                            "attributes": {
                                "draft_registration": {draft_registration_id},               # required, write-only
                                "registration_choice": one of ['embargo', 'immediate'],      # required, write-only
                                "lift_embargo": format %Y-%m-%dT%H:%M:%S'                    # required if registration_choice is 'embargo'
                            }
                        }
                    }
        Success:       201 OK + draft representation

    To create a registration, issue a POST request to the `self` link.  'draft_registration' must be the id of a completed
    draft registration created for the current node.  All required supplemental questions in the draft registration must
    have been answered. Registration choice should be 'embargo' if you wish to add an embargo date to the registration.
    Registrations can have embargo periods for up to four years. 'lift_embargo' should be the embargo end date.
    When the embargo expires, the registration will be made public. If 'immediate' is selected as the "registration_choice",
    the registration will be made public once it is approved.

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ##Registration Schema

    Detailed registration schema.  The schema endpoint is available in `/registration_schema/links/related/href`.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This request/response

    """
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'nodes'
    view_name = 'node-registrations'

    ordering = ('-modified',)

    # overrides ListCreateAPIView
    # TODO: Filter out withdrawals by default
    def get_queryset(self):
        nodes = self.get_node().registrations_all
        auth = get_user_auth(self.request)
        registrations = [node for node in nodes if node.can_view(auth)]
        return registrations

    # overrides ListCreateJSONAPIView
    def perform_create(self, serializer):
        """Create a registration from a draft.
        """
        # On creation, make sure that current user is the creator
        draft_id = self.request.data.get('draft_registration', None)
        draft = self.get_draft(draft_id)
        serializer.save(draft=draft)


class NodeChildrenList(JSONAPIBaseView, bulk_views.ListBulkCreateJSONAPIView, NodeMixin, NodesFilterMixin):
    """Children of the current node. *Writeable*.

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

    ##Actions

    ###Create Child Node

    <!--- Copied Creating New Node from NodeList -->

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "nodes", # required
                           "attributes": {
                             "title":       {title},         # required
                             "category":    {category},      # required
                             "description": {description},   # optional
                             "tags":        [{tag1}, {tag2}] # optional
                           }
                         }
                       }
        Success:       201 CREATED + node representation

    To create a child node of the current node, issue a POST request to this endpoint.  The `title` and `category`
    fields are mandatory. `category` must be one of the [permitted node categories](/v2/#osf-node-categories).  If the
    node creation is successful the API will return a 201 response with the representation of the new node in the body.
    For the new node's canonical URL, see the `/links/self` field of the response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `id`, `title`, `category`, `description`, `public`, `tags`, `date_created`, `date_modified`,
    `root`, `parent`, and `contributors`.  Most are string fields and will be filtered using simple substring matching.  `public`
    is a boolean, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note that quoting `true`
    or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.NODE_CHILDREN_READ]
    required_write_scopes = [CoreScopes.NODE_CHILDREN_WRITE]

    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'node-children'

    ordering = ('-modified',)

    def get_default_queryset(self):
        return default_node_list_queryset(model_cls=Node)

    # overrides ListBulkCreateJSONAPIView
    def get_queryset(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        node_pks = node.node_relations.filter(is_node_link=False).select_related('child')\
                .values_list('child__pk', flat=True)
        return self.get_queryset_from_request().filter(pk__in=node_pks).can_view(auth.user).order_by('-modified')

    # overrides ListBulkCreateJSONAPIView
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(creator=user, parent=self.get_node())


class NodeCitationDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """ The node citation for a node in CSL format *read only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##NodeCitationDetail Attributes

        name                     type                description
        =================================================================================
        id                       string               unique ID for the citation
        title                    string               title of project or component
        author                   list                 list of authors for the work
        publisher                string               publisher - most always 'Open Science Framework'
        type                     string               type of citation - web
        doi                      string               doi of the resource

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeCitationSerializer
    view_category = 'nodes'
    view_name = 'node-citation'

    def get_object(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        if not node.is_public and not node.can_view(auth):
            raise PermissionDenied if auth.user else NotAuthenticated
        return node.csl


class NodeCitationStyleDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """ The node citation for a node in a specific style's format *read only*

        ##Note
        **This API endpoint is under active development, and is subject to change in the future**

    ##NodeCitationDetail Attributes

        name                     type                description
        =================================================================================
        citation                string               complete citation for a node in the given style

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeCitationStyleSerializer
    view_category = 'nodes'
    view_name = 'node-citation'

    def get_object(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        if not node.is_public and not node.can_view(auth):
            raise PermissionDenied if auth.user else NotAuthenticated

        style = self.kwargs.get('style_id')
        try:
            citation = render_citation(node=node, style=style)
        except ValueError as err:  # style requested could not be found
            csl_name = re.findall('[a-zA-Z]+\.csl', err.message)[0]
            raise NotFound('{} is not a known style.'.format(csl_name))

        return {'citation': citation, 'id': style}


# TODO: Make NodeLinks filterable. They currently aren't filterable because we have can't
# currently query on a Pointer's node's attributes.
# e.g. Pointer.find(MQ('node.title', 'eq', ...)) doesn't work
class NodeLinksList(BaseNodeLinksList, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodeMixin):
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
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]
    model_class = NodeRelation

    serializer_class = NodeLinksSerializer
    view_category = 'nodes'
    view_name = 'node-pointers'

    def get_queryset(self):
        return self.get_node().node_relations.select_related('child').filter(is_node_link=True, child__is_deleted=False)

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
            display_name='node'
        )
        if node.is_registration:
            raise MethodNotAllowed(method=self.request.method)
        node = self.get_node()
        try:
            node.rm_pointer(instance, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise ValidationError(err.message)
        node.save()

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeLinksList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeLinksDetail(BaseNodeLinksDetail, generics.RetrieveDestroyAPIView, NodeMixin):
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
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
        RegistrationAndPermissionCheckForPointers,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = NodeLinksSerializer
    view_category = 'nodes'
    view_name = 'node-pointer-detail'
    node_link_lookup_url_kwarg = 'node_link_id'

    # overrides RetrieveAPIView
    def get_object(self):
        node_link = get_object_or_error(
            NodeRelation,
            self.kwargs[self.node_link_lookup_url_kwarg],
            self.request,
            'node link'
        )
        self.check_object_permissions(self.request, node_link.parent)
        return node_link

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_node()
        pointer = self.get_object()
        try:
            node.rm_pointer(pointer, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise NotFound(err.message)
        node.save()


class NodeForksList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin, NodesFilterMixin):
    """Forks of the current node. *Writeable*.

    Paginated list of the current node's forks ordered by their `forked_date`. Forks are copies of projects that you can
    change without affecting the original project.  When creating a fork, your fork will will only contain public components or those
    for which you are a contributor.  Private components that you do not have access to will not be forked. You will receive an email
    when your fork completes.

    ##Node Fork Attributes

    <!--- Copied Attributes from NodeDetail with exception of forked_date-->

    OSF Node Fork entities have the "nodes" `type`.

        name                        type               description
        ===============================================================================================================================
        title                       string             title of project or component
        description                 string             description of the node
        category                    string             node category, must be one of the allowed values
        date_created                iso8601 timestamp  timestamp that the node was created
        modified               iso8601 timestamp  timestamp when the node was last updated
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

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, `tags`, `created`,
    `modified`, `root`, `parent`, and `contributors`. Most are string fields and will be filtered using simple
    substring matching.  Others are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.
    Note that quoting `true` or `false` in the query will cause the match to fail regardless. `tags` is an array of simple strings.

    #This Request/Response
    """
    permission_classes = (
        IsPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.NODE_FORKS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_FORKS_WRITE]

    serializer_class = NodeForksSerializer
    view_category = 'nodes'
    view_name = 'node-forks'

    ordering = ('-forked_date',)

    # overrides ListCreateAPIView
    def get_queryset(self):
        all_forks = self.get_node().forks.exclude(type='osf.registration').order_by('-forked_date')
        auth = get_user_auth(self.request)

        node_pks = [node.pk for node in all_forks if node.can_view(auth)]
        return AbstractNode.objects.filter(pk__in=node_pks)

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        user = get_user_auth(self.request).user
        node = self.get_node()
        try:
            fork = serializer.save(node=node)
        except Exception as exc:
            mails.send_mail(user.email, mails.FORK_FAILED, title=node.title, guid=node._id, mimetype='html', can_change_preferences=False)
            raise exc
        else:
            mails.send_mail(user.email, mails.FORK_COMPLETED, title=node.title, guid=fork._id, mimetype='html', can_change_preferences=False)

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that attributes are not required in request
        """
        res = super(NodeForksList, self).get_parser_context(http_request)
        res['attributes_required'] = False
        return res


class NodeFilesList(JSONAPIBaseView, generics.ListAPIView, WaterButlerMixin, ListFilterMixin, NodeMixin):
    """Files attached to a node for a given provider. *Read-only*.

    This gives a list of all of the files and folders that are attached to your project for the given storage provider.
    If the provider is not "osfstorage", the metadata for the files in the storage will be retrieved and cached whenever
    this endpoint is accessed.  To see the cached metadata, GET the endpoint for the file directly (available through
    its `/links/info` attribute).

    When a create/update/delete action is performed against the file or folder, the action is handled by an external
    service called WaterButler.  The WaterButler response format differs slightly from the OSF's.

    <!--- Copied from FileDetail.Spiel -->

    ###Waterbutler Entities

    When an action is performed against a WaterButler endpoint, it will generally respond with a file entity, a folder
    entity, or no content.

    ####File Entity

        name                        type              description
        ==========================================================================================================
        name                        string            name of the file
        path                        string            unique identifier for this file entity for this
                                                        project and storage provider. may not end with '/'
        materialized                string            the full path of the file relative to the storage
                                                        root.  may not end with '/'
        kind                        string            "file"
        etag                        string            etag - http caching identifier w/o wrapping quotes
        modified                    timestamp         last modified timestamp - format depends on provider
        contentType                 string            MIME-type when available
        provider                    string            id of provider e.g. "osfstorage", "s3", "googledrive".
                                                        equivalent to addon_short_name on the OSF
        size                        integer           size of file in bytes
        current_version             integer           current file version

        current_user_can_comment    boolean           Whether the current user is allowed to post comments

        tags                        array of strings  list of tags that describes the file (osfstorage only)
        extra                       object            may contain additional data beyond what's described here,
                                                       depending on the provider
        version                     integer           version number of file. will be 1 on initial upload
        hashes                      object
        md5                         string            md5 hash of file
        sha256                      string            SHA-256 hash of file

    ####Folder Entity

        name          type    description
        ======================================================================
        name          string  name of the folder
        path          string  unique identifier for this folder entity for this
                              project and storage provider. must end with '/'
        materialized  string  the full path of the folder relative to the storage
                              root.  must end with '/'
        kind          string  "folder"
        etag          string  etag - http caching identifier w/o wrapping quotes
        extra         object  varies depending on provider

    ##File Attributes

    <!--- Copied Attributes from FileDetail -->

    For an OSF File entity, the `type` is "files" regardless of whether the entity is actually a file or folder.  They
    can be distinguished by the `kind` attribute.  Files and folders use the same representation, but some attributes may
    be null for one kind but not the other. `size` will be null for folders.  A list of storage provider keys can be
    found [here](/v2/#storage-providers).

        name          type               description
        ===================================================================================================
        guid              string             OSF GUID for this file (if one has been assigned)
        name              string             name of the file or folder; used for display
        kind              string             "file" or "folder"
        path              string             same as for corresponding WaterButler entity
        materialized_path string             the unix-style path to the file relative to the provider root
        size              integer            size of file in bytes, null for folders
        provider          string             storage provider for this file. "osfstorage" if stored on the
                                             OSF.  other examples include "s3" for Amazon S3, "googledrive"
                                             for Google Drive, "box" for Box.com.
        last_touched      iso8601 timestamp  last time the metadata for the file was retrieved. only
                                             applies to non-OSF storage providers.
        modified     iso8601 timestamp  timestamp of when this file was last updated*
        created      iso8601 timestamp  timestamp of when this file was created*
        extra             object             may contain additional data beyond what's described here,
                                             depending on the provider
          hashes          object
            md5           string             md5 hash of file, null for folders
            sha256        string             SHA-256 hash of file, null for folders
          downloads       integer            number of times the file has been downloaded (for osfstorage files)

    * A note on timestamps: for files stored in osfstorage, `created` refers to the time the file was
    first uploaded to osfstorage, and `date_modified` is the time the file was last updated while in osfstorage.
    Other providers may or may not provide this information, but if they do it will correspond to the provider's
    semantics for created/modified times.  These timestamps may also be stale; metadata retrieved via the File Detail
    endpoint is cached.  The `last_touched` field describes the last time the metadata was retrieved from the external
    provider.  To force a metadata update, access the parent folder via its Node Files List endpoint.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    <!--- Copied from FileDetail.Actions -->

    The `links` property of the response provides endpoints for common file operations. The currently-supported actions
    are:

    ###Get Info (*files, folders*)

        Method:   GET
        URL:      /links/info
        Params:   <none>
        Success:  200 OK + file representation

    The contents of a folder or details of a particular file can be retrieved by performing a GET request against the
    `info` link. The response will be a standard OSF response format with the [OSF File attributes](#attributes).

    ###Download (*files*)

        Method:   GET
        URL:      /links/download
        Params:   <none>
        Success:  200 OK + file body

    To download a file, issue a GET request against the `download` link.  The response will have the Content-Disposition
    header set, which will will trigger a download in a browser.

    ###Create Subfolder (*folders*)

        Method:       PUT
        URL:          /links/new_folder
        Query Params: ?kind=folder&name={new_folder_name}
        Body:         <empty>
        Success:      201 Created + new folder representation

    You can create a subfolder of an existing folder by issuing a PUT request against the `new_folder` link.  The
    `?kind=folder` portion of the query parameter is already included in the `new_folder` link.  The name of the new
    subfolder should be provided in the `name` query parameter.  The response will contain a [WaterButler folder
    entity](#folder-entity).  If a folder with that name already exists in the parent directory, the server will return
    a 409 Conflict error response.

    ###Upload New File (*folders*)

        Method:       PUT
        URL:          /links/upload
        Query Params: ?kind=file&name={new_file_name}
        Body (Raw):   <file data (not form-encoded)>
        Success:      201 Created + new file representation

    To upload a file to a folder, issue a PUT request to the folder's `upload` link with the raw file data in the
    request body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.  The
    response will contain a [WaterButler file entity](#file-entity) that describes the new file.  If a file with the
    same name already exists in the folder, the server will return a 409 Conflict error response.

    ###Update Existing File (*file*)

        Method:       PUT
        URL:          /links/upload
        Query Params: ?kind=file
        Body (Raw):   <file data (not form-encoded)>
        Success:      200 OK + updated file representation

    To update an existing file, issue a PUT request to the file's `upload` link with the raw file data in the request
    body and the `kind` query parameter set to `"file"`.  The update action will create a new version of the file.
    The response will contain a [WaterButler file entity](#file-entity) that describes the updated file.

    ###Rename (*files, folders*)

        Method:        POST
        URL:           /links/move
        Query Params:  <none>
        Body (JSON):   {
                        "action": "rename",
                        "rename": {new_file_name}
                       }
        Success:       200 OK + new entity representation

    To rename a file or folder, issue a POST request to the `move` link with the `action` body parameter set to
    `"rename"` and the `rename` body parameter set to the desired name.  The response will contain either a folder
    entity or file entity with the new name.

    ###Move & Copy (*files, folders*)

        Method:        POST
        URL:           /links/move
        Query Params:  <none>
        Body (JSON):   {
                        // mandatory
                        "action":   "move"|"copy",
                        "path":     {path_attribute_of_target_folder},
                        // optional
                        "rename":   {new_name},
                        "conflict": "replace"|"keep", // defaults to 'replace'
                        "resource": {node_id},        // defaults to current {node_id}
                        "provider": {provider}        // defaults to current {provider}
                       }
        Success:       200 OK or 201 Created + new entity representation

    Move and copy actions both use the same request structure, a POST to the `move` url, but with different values for
    the `action` body parameters.  The `path` parameter is also required and should be the OSF `path` attribute of the
    folder being written to.  The `rename` and `conflict` parameters are optional.  If you wish to change the name of
    the file or folder at its destination, set the `rename` parameter to the new name.  The `conflict` param governs how
    name clashes are resolved.  Possible values are `replace` and `keep`.  `replace` is the default and will overwrite
    the file that already exists in the target folder.  `keep` will attempt to keep both by adding a suffix to the new
    file's name until it no longer conflicts.  The suffix will be ' (**x**)' where **x** is a increasing integer
    starting from 1.  This behavior is intended to mimic that of the OS X Finder.  The response will contain either a
    folder entity or file entity with the new name.

    Files and folders can also be moved between nodes and providers.  The `resource` parameter is the id of the node
    under which the file/folder should be moved.  It *must* agree with the `path` parameter, that is the `path` must
    identify a valid folder under the node identified by `resource`.  Likewise, the `provider` parameter may be used to
    move the file/folder to another storage provider, but both the `resource` and `path` parameters must belong to a
    node and folder already extant on that provider.  Both `resource` and `provider` default to the current node and
    providers.

    If a moved/copied file is overwriting an existing file, a 200 OK response will be returned.  Otherwise, a 201
    Created will be returned.

    ###Delete (*file, folders*)

        Method:        DELETE
        URL:           /links/delete
        Query Params:  <none>
        Success:       204 No Content

    To delete a file or folder send a DELETE request to the `delete` link.  Nothing will be returned in the response
    body.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Node files may be filtered by `id`, `name`, `node`, `kind`, `path`, `provider`, `size`, and `last_touched`.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'node'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    ordering = ('_materialized_path',)  # default ordering

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    view_category = 'nodes'
    view_name = 'node-files'

    @property
    def serializer_class(self):
        if self.kwargs[self.provider_lookup_url_kwarg] == 'osfstorage':
            return OsfStorageFileSerializer
        return FileSerializer

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        # tag queries will usually be on Tag.name,
        # ?filter[tags]=foo should be translated to MQ('tags__name', 'eq', 'foo')
        # But queries on lists should be tags, e.g.
        # ?filter[tags]=foo,bar should be translated to MQ('tags', 'isnull', True)
        # ?filter[tags]=[] should be translated to MQ('tags', 'isnull', True)
        if field_name == 'tags':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = 'tags__name'
                operation['op'] = 'iexact'
        if field_name == 'path':
            operation['source_field_name'] = '_path'
        # NOTE: This is potentially fragile, if we ever add filtering on provider
        # we're going to have to get a bit tricky. get_default_queryset should ramain filtering on BaseFileNode, for now
        if field_name == 'kind':
            if operation['value'].lower() == 'folder':
                kind = Folder
            else:
                # Default to File, should probably raise an exception in the future
                kind = File  # Default to file

            operation['source_field_name'] = 'type'
            operation['op'] = 'in'
            operation['value'] = [
                sub._typedmodels_type
                for sub in kind.__subclasses__()
                if hasattr(sub, '_typedmodels_type')
            ]

    def get_default_queryset(self):
        files_list = self.fetch_from_waterbutler()

        if isinstance(files_list, list):
            provider = self.kwargs[self.provider_lookup_url_kwarg]
            # Resolve to a provider-specific subclass, so that
            # trashed file nodes are filtered out automatically
            ConcreteFileNode = BaseFileNode.resolve_class(provider, BaseFileNode.ANY)
            file_ids = [f.id for f in self.bulk_get_file_nodes_from_wb_resp(files_list)]
            return ConcreteFileNode.objects.filter(id__in=file_ids)

        if isinstance(files_list, list) or not isinstance(files_list, Folder):
            # We should not have gotten a file here
            raise NotFound

        sub_qs = OsfStorageFolder.objects.filter(_children=OuterRef('pk'), pk=files_list.pk)
        return files_list.children.annotate(folder=Exists(sub_qs)).filter(folder=True).prefetch_related('node__guids', 'versions', 'tags', 'guids')

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request().distinct()


class NodeFileDetail(JSONAPIBaseView, generics.RetrieveAPIView, WaterButlerMixin, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'node'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'node'),
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    serializer_class = FileSerializer

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]
    view_category = 'nodes'
    view_name = 'node-file-detail'

    def get_object(self):
        fobj = self.fetch_from_waterbutler()
        if isinstance(fobj, dict):
            # if dict it is a wb response, not file object yet
            return self.get_file_node_from_wb_resp(fobj)

        if isinstance(fobj, list) or not isinstance(fobj, File):
            # We should not have gotten a folder here
            raise NotFound

        return fobj


class NodeAddonList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin, AddonSettingsMixin):
    """List of addons connected to this node *Read-only*

    Paginated list of node addons ordered by their `id` or `addon_short_name`. Attributes other than
    `enabled` will be `null` if the addon is not enabled for this node.

    ## <Addon\>NodeSettings Attributes

    OSF <Addon\>NodeSettings entities have the "node_addons" `type`, and their `id` indicates the addon
    service provider (eg. `box`, `googledrive`, etc).

        name                    type                description
        ======================================================================================================
        external_account_id     string              _id of the associated ExternalAccount, if any
        configured              boolean             has this node been configured with a folder?
        enabled                 boolean             has a node settings object been associated with this node?
        folder_id               string              folder id of linked folder, from third-party service
        node_has_auth           boolean             is this node fully authorized to use an ExternalAccount?
        folder_path             boolean             folder path of linked folder, from third-party service

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        self:  the canonical api endpoint of this node_addon

    #This Request/Response
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeAddonSettingsSerializer
    view_category = 'nodes'
    view_name = 'node-addons'

    ordering = ('-id',)

    def get_default_queryset(self):
        qs = []
        for addon in ADDONS_OAUTH:
            obj = self.get_addon_settings(provider=addon, fail_if_absent=False, check_object_permissions=False)
            if obj:
                qs.append(obj)
        qs.sort()
        return qs

    get_queryset = get_default_queryset


class NodeAddonDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, NodeMixin, AddonSettingsMixin):
    """
    Detail of individual addon connected to this node *Writeable*.

    Attributes other than `enabled` will be null if the addon is not enabled for this node.

    ##Permissions

    <Addon>NodeSettings that are attached to public Nodes will give read-only access to everyone. Private nodes require explicit read
    permission. Write and admin access are the same for public and private nodes. Administrators on a parent node have
    implicit read permissions for all child nodes.

    Any users with write or admin access to the node are able to deauthorize an enabled addon, but only the addon authorizer is able
    to change the configuration (i.e. selected folder) of an already-configured <Addon>NodeSettings entity.

    ## <Addon>NodeSettings Attributes

    OSF <Addon>NodeSettings entities have the "node_addons" `type`, and their `id` indicates the addon
    service provider (eg. `box`, `googledrive`, etc).

        name                    type                description
        ======================================================================================================
        external_account_id     string              _id of the associated ExternalAccount, if any
        configured              boolean             has this node been configured with a folder?
        enabled                 boolean             has a node settings object been associated with this node?
        folder_id               string              folder id of linked folder, from third-party service
        node_has_auth           boolean             is this node fully authorized to use an ExternalAccount?
        folder_path             boolean             folder path of linked folder, from third-party service
        url                     string              Specific to the `forward` addon
        label                   string              Specific to the `forward` addon

    ##Links

        self:  the canonical api endpoint of this node_addon

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {"data": {
                           "type": "node_addons",                   # required
                           "id":   {provider},                      # required
                           "attributes": {
                             "external_account_id": {account_id},   # optional
                             "folder_id":           {folder_id},    # optional
                             "folder_path":         {folder_path},  # optional - Google Drive specific
                             "url":                 {url},          # optional - External Link specific
                             "label":               {label}         # optional - External Link specific
                           }
                         }
                       }
        Success:       200 OK + node_addon representation

    To update a node, issue either a PUT or a PATCH request against the `/links/self` URL.  The `external_account_id`,
    `enabled`, and `folder_id` fields are mandatory if you PUT and optional if you PATCH. However, at least one is always mandatory.
    Non-string values will be accepted and stringified, but we make no promises about the stringification output.  So
    don't do that.

    To delete or deauthorize a node_addon, issue a PUT with all fields set to `null` / `False`, or a PATCH with `enabled` set to `False`.

    ####Note

    Not all addons are currently configurable via the API. The current list of addons that accept PUT/PATCH is [`box`, `dropbox`, `s3`, `googledrive`]

    #This Request/Response
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ]
    required_write_scopes = [CoreScopes.NODE_ADDON_WRITE]

    serializer_class = NodeAddonSettingsSerializer
    view_category = 'nodes'
    view_name = 'node-addon-detail'

    def get_object(self):
        return self.get_addon_settings(check_object_permissions=False)

    def perform_create(self, serializer):
        addon = self.kwargs['provider']
        if addon not in ADDONS_OAUTH:
            raise NotFound('Requested addon unavailable')

        node = self.get_node()
        if node.has_addon(addon):
            raise InvalidModelValueError(
                detail='Add-on {} already enabled for node {}'.format(addon, node._id)
            )

        return super(NodeAddonDetail, self).perform_create(serializer)

    def perform_destroy(self, instance):
        addon = instance.config.short_name
        node = self.get_node()
        if not node.has_addon(instance.config.short_name):
            raise NotFound('Node {} does not have add-on {}'.format(node._id, addon))

        node.delete_addon(addon, auth=get_user_auth(self.request))

    def get_serializer_class(self):
        """
        Use NodeDetailSerializer which requires 'id'
        """
        if 'provider' in self.kwargs and self.kwargs['provider'] == 'forward':
            return ForwardNodeAddonSettingsSerializer
        else:
            return NodeAddonSettingsSerializer


class NodeAddonFolderList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, AddonSettingsMixin):
    """List of folders that this node can connect to *Read-only*.

    Paginated list of folders retrieved from the associated third-party service

    ##Permissions

    <Addon> Folders are visible only to the addon authorizer.

    ## <Addon> Folder Attributes

    OSF <Addon\> Folder entities have the "node_addon_folders" `type`, and their `id` indicates the folder_id
    according to the associated service provider (eg. `box`, `googledrive`, etc).

        name        type        description
        ======================================================================================================
        path        string      path of this folder, according to third-party service
        kind        string      `"folder"`, typically.
        provider    string      `short_name` of third-party service provider
        name        string      name of this folder
        folder_id   string      id of this folder, according to third-party service

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

        root:  the canonical api endpoint of the root folder for this account
        children: the canonical api endpoint of this folder's children

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ, CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NULL]

    pagination_class = MaxSizePagination
    serializer_class = NodeAddonFolderSerializer
    view_category = 'nodes'
    view_name = 'node-addon-folders'

    def get_queryset(self):
        # TODO: [OSF-6120] refactor this/NS models to be generalizable
        node_addon = self.get_addon_settings()
        if not node_addon.has_auth:
            raise JSONAPIException(detail='This addon is enabled but an account has not been imported from your user settings',
                meta={'link': '{}users/me/addons/{}/accounts/'.format(API_BASE, node_addon.config.short_name)})

        path = self.request.query_params.get('path')
        folder_id = self.request.query_params.get('id')

        if not hasattr(node_addon, 'get_folders'):
            raise EndpointNotImplementedError('Endpoint not yet implemented for this addon')

        return node_addon.get_folders(path=path, folder_id=folder_id)


class NodeProvider(object):

    def __init__(self, provider, node):
        self.path = '/'
        self.node = node
        self.kind = 'folder'
        self.name = provider
        self.provider = provider
        self.node_id = node._id
        self.pk = node._id
        self.id = node.id


class NodeProvidersList(JSONAPIBaseView, generics.ListAPIView, NodeMixin):
    """List of storage providers enabled for this node. *Read-only*.

    Users of the OSF may access their data on a [number of cloud-storage](/v2/#storage-providers) services that have
    integrations with the OSF.  We call these "providers".  By default every node has access to the OSF-provided
    storage but may use as many of the supported providers as desired.  This endpoint lists all of the providers that are
    configured for this node.  If you want to add more, you will need to do that in the Open Science Framework front end
    for now.

    In the OSF filesystem model, providers are treated as folders, but with special properties that distinguish them
    from regular folders.  Every provider folder is considered a root folder, and may not be deleted through the regular
    file API.  To see the contents of the provider, issue a GET request to the `/relationships/files/links/related/href`
    attribute of the provider resource.  The `new_folder` and `upload` actions are handled by another service called
    WaterButler, whose response format differs slightly from the OSF's.

    <!--- Copied from FileDetail.Spiel -->

    ###Waterbutler Entities

    When an action is performed against a WaterButler endpoint, it will generally respond with a file entity, a folder
    entity, or no content.

    ####File Entity

        name          type       description
        =========================================================================
        name          string     name of the file
        path          string     unique identifier for this file entity for this
                                 project and storage provider. may not end with '/'
        materialized  string     the full path of the file relative to the storage
                                 root.  may not end with '/'
        kind          string     "file"
        etag          string     etag - http caching identifier w/o wrapping quotes
        modified      timestamp  last modified timestamp - format depends on provider
        contentType   string     MIME-type when available
        provider      string     id of provider e.g. "osfstorage", "s3", "googledrive".
                                 equivalent to addon_short_name on the OSF
        size          integer    size of file in bytes
        extra         object     may contain additional data beyond what's described here,
                                 depending on the provider
          version     integer    version number of file. will be 1 on initial upload
          downloads   integer    count of the number times the file has been downloaded
          hashes      object
            md5       string     md5 hash of file
            sha256    string     SHA-256 hash of file

    ####Folder Entity

        name          type    description
        ======================================================================
        name          string  name of the folder
        path          string  unique identifier for this folder entity for this
                              project and storage provider. must end with '/'
        materialized  string  the full path of the folder relative to the storage
                              root.  must end with '/'
        kind          string  "folder"
        etag          string  etag - http caching identifier w/o wrapping quotes
        extra         object  varies depending on provider

    ##Provider Attributes

    `type` is "files"

        name      type    description
        =================================================================================
        name      string  name of the provider
        kind      string  type of this file/folder.  always "folder"
        path      path    relative path of this folder within the provider filesys. always "/"
        node      string  node this provider belongs to
        provider  string  provider id, same as "name"

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    <!--- Copied from FileDetail.Actions -->

    ###Create Subfolder (*folders*)

        Method:       PUT
        URL:          /links/new_folder
        Query Params: ?kind=folder&name={new_folder_name}
        Body:         <empty>
        Success:      201 Created + new folder representation

    You can create a subfolder of an existing folder by issuing a PUT request against the `new_folder` link.  The
    `?kind=folder` portion of the query parameter is already included in the `new_folder` link.  The name of the new
    subfolder should be provided in the `name` query parameter.  The response will contain a [WaterButler folder
    entity](#folder-entity).  If a folder with that name already exists in the parent directory, the server will return
    a 409 Conflict error response.

    ###Upload New File (*folders*)

        Method:       PUT
        URL:          /links/upload
        Query Params: ?kind=file&name={new_file_name}
        Body (Raw):   <file data (not form-encoded)>
        Success:      201 Created + new file representation

    To upload a file to a folder, issue a PUT request to the folder's `upload` link with the raw file data in the
    request body, and the `kind` and `name` query parameters set to `'file'` and the desired name of the file.  The
    response will contain a [WaterButler file entity](#file-entity) that describes the new file.  If a file with the
    same name already exists in the folder, the server will return a 409 Conflict error response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeProviderSerializer
    view_category = 'nodes'
    view_name = 'node-providers'

    ordering = ('-id',)

    def get_provider_item(self, provider):
        return NodeProvider(provider, self.get_node())

    def get_queryset(self):
        return [
            self.get_provider_item(addon.config.short_name) for
            addon in
            self.get_node().get_addons() if
            addon.config.has_hgrid_files and
            addon.configured
        ]

class NodeProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeProviderSerializer
    view_category = 'nodes'
    view_name = 'node-provider-detail'

    def get_object(self):
        return NodeProvider(self.kwargs['provider'], self.get_node())


class NodeLogList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, ListFilterMixin):
    """List of Logs associated with a given Node. *Read-only*.

    <!--- Copied Description from NodeLogDetail -->

    Paginated list of Logs ordered by their `date`. This includes the Logs of the specified Node as well as the logs of that Node's children that the current user has access to.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    On the front end, logs show record and show actions done on the OSF. The complete list of loggable actions (in the format {identifier}: {description}) is as follows:

    * 'project_created': A Node is created
    * 'project_registered': A Node is registered
    * 'project_deleted': A Node is deleted
    * 'created_from': A Node is created using an existing Node as a template
    * 'pointer_created': A Pointer is created
    * 'pointer_forked': A Pointer is forked
    * 'pointer_removed': A Pointer is removed
    * 'node_removed': A component is deleted
    * 'node_forked': A Node is forked
    ===
    * 'made_public': A Node is made public
    * 'made_private': A Node is made private
    * 'tag_added': A tag is added to a Node
    * 'tag_removed': A tag is removed from a Node
    * 'edit_title': A Node's title is changed
    * 'edit_description': A Node's description is changed
    * 'updated_fields': One or more of a Node's fields are changed
    * 'external_ids_added': An external identifier is added to a Node (e.g. DOI, ARK)
    ===
    * 'contributor_added': A Contributor is added to a Node
    * 'contributor_removed': A Contributor is removed from a Node
    * 'contributors_reordered': A Contributor's position in a Node's bibliography is changed
    * 'permissions_updated': A Contributor's permissions on a Node are changed
    * 'made_contributor_visible': A Contributor is made bibliographically visible on a Node
    * 'made_contributor_invisible': A Contributor is made bibliographically invisible on a Node
    ===
    * 'wiki_updated': A Node's wiki is updated
    * 'wiki_deleted': A Node's wiki is deleted
    * 'wiki_renamed': A Node's wiki is renamed
    * 'made_wiki_public': A Node's wiki is made public
    * 'made_wiki_private': A Node's wiki is made private
    ===
    * 'addon_added': An add-on is linked to a Node
    * 'addon_removed': An add-on is unlinked from a Node
    * 'addon_file_moved': A File in a Node's linked add-on is moved
    * 'addon_file_copied': A File in a Node's linked add-on is copied
    * 'addon_file_renamed': A File in a Node's linked add-on is renamed
    * 'node_authorized': An addon is authorized for a project
    * 'node_deauthorized': An addon is deauthorized for a project
    * 'folder_created': A Folder is created in a Node's linked add-on
    * 'file_added': A File is added to a Node's linked add-on
    * 'file_updated': A File is updated on a Node's linked add-on
    * 'file_removed': A File is removed from a Node's linked add-on
    * 'file_restored': A File is restored in a Node's linked add-on
    ===
    * 'comment_added': A Comment is added to some item
    * 'comment_removed': A Comment is removed from some item
    * 'comment_updated': A Comment is updated on some item
    ===
    * 'embargo_initiated': An embargoed Registration is proposed on a Node
    * 'embargo_approved': A proposed Embargo of a Node is approved
    * 'embargo_cancelled': A proposed Embargo of a Node is cancelled
    * 'embargo_completed': A proposed Embargo of a Node is completed
    * 'retraction_initiated': A Withdrawal of a Registration is proposed
    * 'retraction_approved': A Withdrawal of a Registration is approved
    * 'retraction_cancelled': A Withdrawal of a Registration is cancelled
    * 'registration_initiated': A Registration of a Node is proposed
    * 'registration_approved': A proposed Registration is approved
    * 'registration_cancelled': A proposed Registration is cancelled
    ===
    * 'node_created': A Node is created (_deprecated_)

   ##Log Attributes

    <!--- Copied Attributes from LogList -->

    OSF Log entities have the "logs" `type`.

        name           type                   description
        ============================================================================
        date           iso8601 timestamp      timestamp of Log creation
        action         string                 Log action (see list above)

    ##Relationships

    ###Node

    The node this log belongs to.

    ###User

    The user who performed the logged action.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ##Query Params

    <!--- Copied Query Params from LogList -->

    Logs may be filtered by their `action` and `date`.

    #This Request/Response

    """

    serializer_class = NodeLogSerializer
    view_category = 'nodes'
    view_name = 'node-logs'

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    log_lookup_url_kwarg = 'node_id'

    ordering = ('-date', )

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        return self.get_node().get_aggregate_logs_queryset(auth)

    def get_queryset(self):
        return self.get_queryset_from_request().include(
            'node__guids', 'user__guids', 'original_node__guids', limit_includes=10
        )


class NodeCommentsList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, NodeMixin):
    """List of comments on a node. *Writeable*.

    Paginated list of comments ordered by their `created.` Each resource contains the full representation of the
    comment, meaning additional requests to an individual comment's detail view are not necessary.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ###Permissions

    Comments on public nodes are given read-only access to everyone. If the node comment-level is "private",
    only contributors have permission to comment. If the comment-level is "public" any logged-in OSF user can comment.
    Comments on private nodes are only visible to contributors and administrators on the parent node.

    ##Attributes

    OSF comment entities have the "comments" `type`.

        name           type               description
        =================================================================================
        content        string             content of the comment
        created        iso8601 timestamp  timestamp that the comment was created
        modified       iso8601 timestamp  timestamp when the comment was last updated
        edited         boolean            has this comment been edited?
        deleted        boolean            is this comment deleted?
        is_abuse       boolean            has this comment been reported by the current user?
        has_children   boolean            does this comment have replies?
        can_edit       boolean            can the current user edit this comment?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "comments",   # required
                           "attributes": {
                             "content":       {content},        # mandatory
                           },
                           "relationships": {
                             "target": {
                               "data": {
                                  "type": {target type}         # mandatory
                                  "id": {target._id}            # mandatory
                               }
                             }
                           }
                         }
                       }
        Success:       201 CREATED + comment representation

    To create a comment on this node, issue a POST request against this endpoint. The comment target id and target type
    must be specified. To create a comment on the node overview page, the target `type` would be "nodes" and the `id`
    would be the node id. To reply to a comment on this node, the target `type` would be "comments" and the `id` would
    be the id of the comment to reply to. The `content` field is mandatory.

    If the comment creation is successful the API will return
    a 201 response with the representation of the new comment in the body. For the new comment's canonical URL, see the
    `/links/self` field of the response.

    ##Query Params

    + `filter[deleted]=True|False` -- filter comments based on whether or not they are deleted.

    The list of node comments includes deleted comments by default. The `deleted` field is a boolean and can be
    filtered using truthy values, such as `true`, `false`, `0`, or `1`. Note that quoting `true` or `false` in
    the query will cause the match to fail regardless.

    + `filter[created][comparison_operator]=YYYY-MM-DDTH:M:S` -- filter comments based on date created.

    Comments can also be filtered based on their `created` and `modified` fields. Possible comparison
    operators include 'gt' (greater than), 'gte'(greater than or equal to), 'lt' (less than) and 'lte'
    (less than or equal to). The date must be in the format YYYY-MM-DD and the time is optional.

    + `filter[target]=target_id` -- filter comments based on their target id.

    The list of comments can be filtered by target id. For example, to get all comments with target = project,
    the target_id would be the project_id.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanCommentOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    pagination_class = CommentPagination
    serializer_class = NodeCommentSerializer
    view_category = 'nodes'
    view_name = 'node-comments'

    ordering = ('-created', )  # default ordering

    def get_default_queryset(self):
        return Comment.objects.filter(node=self.get_node(), root_target__isnull=False)

    # Hook to make filtering on 'target' work
    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'target':
            operation['value'] = Guid.load(operation['value'])

    def get_queryset(self):
        comments = self.get_queryset_from_request()
        for comment in comments:
            # Deleted root targets still appear as tuples in the database,
            # but need to be None in order for the query to be correct.
            if comment.root_target.referent.is_deleted:
                comment.root_target = None
                comment.save()
        return comments

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        else:
            return NodeCommentSerializer

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeCommentsList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res

    def perform_create(self, serializer):
        node = self.get_node()
        serializer.validated_data['user'] = self.request.user
        serializer.validated_data['node'] = node
        serializer.save()


class NodeInstitutionsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin):
    """ Detail of the affiliated institutions a node has, if any. Returns [] if the node has no
    affiliated institution.

    ##Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        =========================================================================
        name           string             title of the institution
        id             string             unique identifier in the OSF
        logo_path      string             a path to the institution's static logo



    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        AdminOrPublic
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = InstitutionSerializer

    model = Institution
    view_category = 'nodes'
    view_name = 'node-institutions'

    ordering = ('-id',)

    def get_queryset(self):
        node = self.get_node()
        return node.affiliated_institutions.all() or []


class NodeInstitutionsRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, NodeMixin):
    """ Relationship Endpoint for Node -> Institutions Relationship

    Used to set, remove, update and retrieve the affiliated_institutions of a node to an institution

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       201

        This requires write permissions on the node and for the user making the request to
        have the institutions in the payload as affiliated in their account.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       200

        This requires write permissions on the node and for the user making the request to
        have the institutions in the payload as affiliated in their account. This will delete
        all institutions not listed, meaning a data: [] payload does the same as a DELETE with all
        the institutions.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       204

        This requires write permissions in the node. If the user has admin permissions, the institution in the payload does
        not need to be affiliated in their account.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        WriteOrPublicForRelationshipInstitutions
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    serializer_class = NodeInstitutionsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'nodes'
    view_name = 'node-relationships-institutions'

    def get_object(self):
        node = self.get_node(check_object_permissions=False)
        obj = {
            'data': node.affiliated_institutions.all(),
            'self': node
        }
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_insts = {inst._id: inst for inst in instance['data']}
        node = instance['self']

        for val in data:
            if val['id'] in current_insts:
                if not user.is_affiliated_with_institution(current_insts[val['id']]) and not node.has_permission(user, 'admin'):
                    raise PermissionDenied
                node.remove_affiliated_institution(inst=current_insts[val['id']], user=user)
        node.save()

    def create(self, *args, **kwargs):
        try:
            ret = super(NodeInstitutionsRelationship, self).create(*args, **kwargs)
            # timestamp_pattern create
            for data in self.request.data['data']:
                institution_id = Institution.objects.get(_id=data['id']).id
                guid = kwargs['node_id']
                timestampPattern, _ = RdmTimestampGrantPattern.objects.get_or_create(
                    institution_id=institution_id, node_guid=guid)
                timestampPattern.save()
        except RelationshipPostMakesNoChanges:
            return Response(status=HTTP_204_NO_CONTENT)
        return ret


class NodeWikiList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, ListFilterMixin):
    """List of wiki pages on a node. *Read only*.

    Paginated list of the node's current wiki page versions ordered by their `date_modified.` Each resource contains the
    full representation of the wiki, meaning additional requests to an individual wiki's detail view are not necessary.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ###Permissions

    Wiki pages on public nodes are given read-only access to everyone. Wiki pages on private nodes are only visible to
    contributors and administrators on the parent node.

    ##Attributes

    OSF wiki entities have the "wikis" `type`.

        name                    type               description
        ======================================================================================================
        name                        string             name of the wiki pag
        path                        string             the path of the wiki page
        materialized_path           string             the path of the wiki page
        date_modified               iso8601 timestamp  timestamp when the wiki was last updated
        content_type                string             MIME-type
        current_user_can_comment    boolean            Whether the current user is allowed to post comments
        extra                       object
        version                     integer            version number of the wiki


    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `filter[name]=<Str>` -- filter wiki pages by name

    + `filter[date_modified][comparison_operator]=YYYY-MM-DDTH:M:S` -- filter wiki pages based on date modified.

    Wiki pages can be filtered based on their `date_modified` fields. Possible comparison
    operators include 'gt' (greater than), 'gte'(greater than or equal to), 'lt' (less than) and 'lte'
    (less than or equal to). The date must be in the format YYYY-MM-DD and the time is optional.


    #This Request/Response
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = NodeWikiSerializer

    view_category = 'nodes'
    view_name = 'node-wikis'

    ordering = ('-date', )  # default ordering

    def get_default_queryset(self):
        node = self.get_node()
        node_wiki_pages = node.wiki_pages_current.values() if node.wiki_pages_current else []
        return NodeWikiPage.objects.filter(guids___id__in=node_wiki_pages)

    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeLinkedNodesRelationship(LinkedNodesRelationship, NodeMixin):
    """ Relationship Endpoint for Nodes -> Linked Node relationships

    Used to set, remove, update and retrieve the ids of the linked nodes attached to this collection. For each id, there
    exists a node link that contains that node.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the nodes requested. Data can be contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this collection.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the nodes requested. Data can be contain any number of
    node identifiers. This will replace the contents of the node_links for this collection with
    the contents of the request. It will delete all node links that don't have a node_id in the data
    array, create node links for the node_ids that don't currently have a node id, and do nothing
    for node_ids that already have a corresponding node_link. This means a update request with
    {"data": []} will remove all node_links in this collection

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """

    view_category = 'nodes'
    view_name = 'node-pointer-relationship'


class LinkedNodesList(BaseLinkedList, NodeMixin):
    """List of nodes linked to this node. *Read-only*.

    Linked nodes are the nodes pointed to by node links. This view will probably replace node_links in the near future.

    <!--- Copied Spiel from NodeDetail -->

    On the front end, nodes are considered 'projects' or 'components'. The difference between a project and a component
    is that a project is the top-level node, and components are children of the project. There is also a [category
    field](/v2/#osf-node-categories) that includes 'project' as an option. The categorization essentially determines
    which icon is displayed by the node in the front-end UI and helps with search organization. Top-level nodes may have
    a category other than project, and children nodes may have a category of project.

    ##Linked Node Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name           type               description
        =================================================================================
        title          string             title of project or component
        description    string             description of the node
        category       string             node category, must be one of the allowed values
        created   iso8601 timestamp  timestamp that the node was created
        modified  iso8601 timestamp  timestamp when the node was last updated
        tags           array of strings   list of tags that describe the node
        registration   boolean            is this is a registration?
        collection     boolean            is this node a collection of other nodes?
        public         boolean            has this node been made publicly-visible?

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
    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'linked-nodes'

    def get_queryset(self):
        queryset = super(LinkedNodesList, self).get_queryset()
        return queryset.exclude(type='osf.registration')

    # overrides APIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(LinkedNodesList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeLinkedRegistrationsRelationship(LinkedRegistrationsRelationship, NodeMixin):
    """ Relationship Endpoint for Node -> Linked Registration relationships

    Used to set, remove, update and retrieve the ids of the linked registrations attached to this node. For each id, there
    exists a node link that contains that node.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the node, and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this node.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the node, and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
    node identifiers. This will replace the contents of the node_links for this node with
    the contents of the request. It will delete all node links that don't have a node_id in the data
    array, create node links for the node_ids that don't currently have a node id, and do nothing
    for node_ids that already have a corresponding node_link. This means a update request with
    {"data": []} will remove all node_links in this node.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """

    view_category = 'nodes'
    view_name = 'node-registration-pointer-relationship'


class NodeLinkedRegistrationsList(BaseLinkedList, NodeMixin):
    """List of registrations linked to this node. *Read-only*.

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
        created                         iso8601 timestamp  timestamp that the node was created
        modified                        iso8601 timestamp  timestamp when the node was last updated
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
    view_category = 'nodes'
    view_name = 'linked-registrations'

    def get_queryset(self):
        ret = [node for node in
            super(NodeLinkedRegistrationsList, self).get_queryset()
            if node.is_registration]
        return ret

    # overrides APIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeLinkedRegistrationsList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeViewOnlyLinksList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, NodeMixin):
    """
    List of view only links on a node. *Writeable*.

    ###Permissions

    View only links on a node, public or private, are readable and writeable only by users that are
    administrators on the node.

    ##Attributes

        name            type                    description
        =================================================================================
        name            string                  name of the view only link
        anonymous       boolean                 whether the view only link has anonymized contributors
        created         iso8601 timestamp       timestamp when the view only link was created
        key             string                  the view only link key


    ##Relationships

    ###Creator

    The user who created the view only link.

    ###Nodes

    The nodes which this view only link key gives read-only access to.

    ##Actions

    ###Create

        Method:        POST
        Body (JSON): {
                        "data": {
                            "attributes": {
                                "name": {string},              #optional
                                "anonymous": true|false,        #optional
                            }
                        }
                    }
        Success:       201 CREATED + VOL representation

    ##Query Params

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    View only links may be filtered by their `name`, `anonymous`, and `created` attributes.

    #This Request/Response
    """
    permission_classes = (
        IsAdmin,
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeViewOnlyLinkSerializer

    view_category = 'nodes'
    view_name = 'node-view-only-links'

    ordering = ('-created',)

    def get_default_queryset(self):
        return self.get_node().private_links.filter(is_deleted=False)

    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, NodeMixin):
    """
    Detail of a specific view only link on a node. *Writeable*.

    ###Permissions

    View only links on a node, public or private, are only readable and writeable by users that are
    administrators on the node.

    ##Attributes

        name            type                    description
        =================================================================================
        name            string                  name of the view only link
        anonymous       boolean                 whether the view only link has anonymized contributors
        created         iso8601 timestamp       timestamp when the view only link was created
        key             string                  the view only key


    ##Relationships

    ###Creator

    The user who created the view only link.

    ###Nodes

    The nodes which this view only link key gives read-only access to.

    ##Actions

    ###Update

        Method:        PUT
        Body (JSON):   {
                         "data": {
                           "attributes": {
                             "name": {string},               #optional
                             "anonymous": true|false,        #optional
                           },
                         }
                       }
        Success:       200 OK + VOL representation

    ###Delete

        Method:        DELETE
        Body (JSON):   <none>
        Success:       204 NO CONTENT

    #This Request/Response
    """

    permission_classes = (
        IsAdmin,
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeViewOnlyLinkSerializer

    view_category = 'nodes'
    view_name = 'node-view-only-link-detail'

    def get_serializer_class(self):
        if self.request.method == 'PUT':
            return NodeViewOnlyLinkUpdateSerializer
        return NodeViewOnlyLinkSerializer

    def get_object(self):
        try:
            return self.get_node().private_links.get(_id=self.kwargs['link_id'])
        except PrivateLink.DoesNotExist:
            raise NotFound

    def perform_destroy(self, link):
        assert isinstance(link, PrivateLink), 'link must be a PrivateLink'
        link.is_deleted = True
        link.save()
        enqueue_postcommit_task(ban_url, (self.get_node(),), {}, celery=True, once_per_request=True)


class NodeIdentifierList(NodeMixin, IdentifierList):
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

    serializer_class = NodeIdentifierSerializer
    node_lookup_url_kwarg = 'node_id'

    # overrides IdentifierList
    def get_object(self, check_object_permissions=True):
        return self.get_node(check_object_permissions=check_object_permissions)

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
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


class NodePreprintsList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, PreprintFilterMixin):
    """List of preprints for a node. *Read-only*.

    ##Note
    **This API endpoint is under active development, and is subject to change in the future.**

    Paginated list of preprints ordered by their `created`.  Each resource contains a representation of the
    preprint.

    ##Preprint Attributes

    OSF Preprint entities have the "preprints" `type`.

        name                            type                                description
        ====================================================================================
        created                         iso8601 timestamp                   timestamp that the preprint was created
        modified                        iso8601 timestamp                   timestamp that the preprint was last modified
        date_published                  iso8601 timestamp                   timestamp when the preprint was published
        original_publication_date       iso8601 timestamp                   user-entered date of publication from external posting
        is_published                    boolean                             whether or not this preprint is published
        is_preprint_orphan              boolean                             whether or not this preprint is orphaned
        subjects                        list of lists of dictionaries       ids of Subject in the BePress taxonomy. Dictrionary, containing the subject text and subject ID
        provider                        string                              original source of the preprint
        doi                             string                              bare DOI for the manuscript, as entered by the user

    ##Relationships

    ###Node
    The node that this preprint was created for

    ###Primary File
    The file that is designated as the preprint's primary file, or the manuscript of the preprint.

    ###Provider
    Link to preprint_provider detail for this preprint

    ##Links

    - `self` -- Preprint detail page for the current preprint
    - `html` -- Project on the OSF corresponding to the current preprint
    - `doi` -- URL representation of the DOI entered by the user for the preprint manuscript

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'nodes'
    view_name = 'node-preprints'

    ordering = ('-modified',)

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)
        node = self.get_node()
        # Permissions on the node are handled by the permissions_classes
        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(node.preprints.all(), auth_user)

    def get_queryset(self):
        return self.get_queryset_from_request()
