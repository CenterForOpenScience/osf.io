from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from rest_framework.response import Response

from framework.auth.oauth_scopes import CoreScopes

from api.base import generic_bulk_views as bulk_views
from api.base import permissions as base_permissions
from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.parsers import JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON
from api.base.utils import get_object_or_error, is_bulk_request, get_user_auth
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.base.serializers import LinkedNodesRelationshipSerializer
from api.collections.serializers import (
    CollectionSerializer,
    CollectionDetailSerializer,
    CollectionNodeLinkSerializer,
)
from api.nodes.serializers import NodeSerializer

from api.nodes.permissions import (
    ContributorOrPublic,
    ReadOnlyIfRegistration,
    ContributorOrPublicForPointers,
    ContributorOrPublicForRelationshipPointers,
)

from website.exceptions import NodeStateError
from website.models import Node, Pointer
from website.util.permissions import ADMIN


class CollectionMixin(object):
    """Mixin with convenience methods for retrieving the current collection based on the
    current URL. By default, fetches the current node based on the collection_id kwarg.
    """

    serializer_class = CollectionSerializer
    node_lookup_url_kwarg = 'collection_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='collection'
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a non-collection through a collection endpoint, we return a 404
        if not node.is_collection:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class CollectionList(JSONAPIBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, ODMFilterMixin):
    """Organizer Collections organize projects and components. *Writeable*.

    Paginated list of Project Organizer Collections ordered by their `date_modified`.
    Each resource contains the full representation of the project organizer collection, meaning additional
    requests to an individual Organizer Collection's detail view are not necessary.

    The Project Organizer is a tool to allow the user to make Collections of projects, components, and registrations
    for whatever purpose the user might want to organize them. They make node_links to any Node that a user has
    read access to. Collections through this API do not nest. Currently Collections are private to any individual user,
    though that could change one day.

    ##Collection Attributes

    OSF Organizer Collection entities have the "nodes" `type`.

        name           type               description
        =================================================================================
        title          string             title of Organizer Collection
        date_created   iso8601 timestamp  timestamp that the collection was created
        date_modified  iso8601 timestamp  timestamp when the collection was last updated


    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Creating New Organizer Collections

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "collections", # required
                           "attributes": {
                             "title":       {title},          # required
                           }
                         }
                        }
        Success:       201 CREATED + collection representation

    New Organizer Collections are created by issuing a POST request to this endpoint.  The `title` field is
    mandatory. All other fields not listed above will be ignored.  If the Organizer Collection creation is successful
    the API will return a 201 response with the representation of the new node in the body.
    For the new Collection's canonical URL, see the `/links/self` field of the response.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Organizer Collections may be filtered by their `title`, which is a string field and will be filtered using simple
    substring matching.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ORGANIZER_COLLECTIONS_BASE_READ]
    required_write_scopes = [CoreScopes.ORGANIZER_COLLECTIONS_BASE_WRITE]

    serializer_class = CollectionSerializer
    view_category = 'collections'
    view_name = 'collection-list'
    model_class = Node

    ordering = ('-date_modified', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_collection', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        # For bulk requests, queryset is formed from request body.
        if is_bulk_request(self.request):
            query = Q('_id', 'in', [node['id'] for node in self.request.data])

            auth = get_user_auth(self.request)
            nodes = Node.find(query)
            for node in nodes:
                if not node.can_edit(auth):
                    raise PermissionDenied
            return nodes
        else:
            query = self.get_query_from_request()
            return Node.find(query)

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView, BulkDestroyJSONAPIView
    def get_serializer_class(self):
        """
        Use CollectionDetailSerializer which requires 'id'
        """
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return CollectionDetailSerializer
        else:
            return CollectionSerializer

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
        for node in resource_list:
            if not node.has_permission(user, ADMIN):
                return False
        return True

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        try:
            instance.remove_node(auth=auth)
        except NodeStateError as err:
            raise ValidationError(err.message)
        instance.save()


class CollectionDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, CollectionMixin):
    """Details about Organizer Collections. *Writeable*.

    The Project Organizer is a tool to allow the user to make Collections of projects, components, and registrations
    for whatever purpose the user might want to organize them. They make node_links to any Node that a user has
    read access to. Collections through this API do not nest. Currently Collections are private to any individual user,
    though that could change one day.

    ##Collection Attributes

    OSF Organizer Collection entities have the "nodes" `type`.

        name           type               description
        =================================================================================
        title          string             title of Organizer Collection
        date_created   iso8601 timestamp  timestamp that the collection was created
        date_modified  iso8601 timestamp  timestamp when the collection was last updated

    ##Relationships

    ###Node links

    Node links are pointers or aliases to nodes. This relationship lists all of the nodes that the Organizer Collection
    is pointing to. New node links can be created with this collection.

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
                           }
                         }
                       }
        Success:       200 OK + node representation

    To update an Organizer Collection, issue either a PUT or a PATCH request against the `/links/self` URL.
    The `title` field is mandatory if you PUT and optional if you PATCH, though there's no reason to PATCH if you aren't
    changing the name. Non-string values will be accepted and stringified, but we make no promises about the
    stringification output.  So don't do that.

    ###Delete

        Method:   DELETE
        URL:      /links/self
        Params:   <none>
        Success:  204 No Content

    To delete a node, issue a DELETE request against `/links/self`.  A successful delete will return a 204 No Content
    response. Attempting to delete a node you do not own will result in a 403 Forbidden.

    ##Query Params

    *None*.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ORGANIZER_COLLECTIONS_BASE_READ]
    required_write_scopes = [CoreScopes.ORGANIZER_COLLECTIONS_BASE_WRITE]

    serializer_class = CollectionDetailSerializer
    view_category = 'collections'
    view_name = 'collection-detail'

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


class LinkedNodesList(JSONAPIBaseView, generics.ListAPIView, CollectionMixin):
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
        date_created   iso8601 timestamp  timestamp that the node was created
        date_modified  iso8601 timestamp  timestamp when the node was last updated
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
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = NodeSerializer
    view_category = 'collections'
    view_name = 'linked-nodes'

    model_class = Pointer

    def get_queryset(self):
        auth = get_user_auth(self.request)
        return sorted([
            pointer.node for pointer in
            self.get_node().nodes_pointer
            if not pointer.node.is_deleted and not pointer.node.is_collection and
            pointer.node.can_view(auth)
        ], key=lambda n: n.date_modified, reverse=True)

    # overrides APIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(LinkedNodesList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeLinksList(JSONAPIBaseView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, CollectionMixin):
    """Node Links to other nodes. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Node Link Attributes

    *None*

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Create
        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "node_links", # required
                         },
                         'relationships': {
                            'target_node': {
                                'data': {
                                    'type': 'nodes',
                                    'id': '<node_id>'
                                }
                            }
                        }


    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = CollectionNodeLinkSerializer
    view_category = 'collections'
    view_name = 'node-pointers'
    model_class = Pointer

    def get_queryset(self):
        return [
            pointer for pointer in
            self.get_node().nodes_pointer
            if not pointer.node.is_deleted and not pointer.node.is_collection
        ]

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
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


class NodeLinksDetail(JSONAPIBaseView, generics.RetrieveDestroyAPIView, CollectionMixin):
    """Node Link details. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Attributes

    *None*

    ##Relationships

    ##Links

    self:  the canonical api endpoint of this node

    ##Actions

    ###Delete

        Method:   DELETE
        URL:      /links/self
        Params:   <none>
        Success:  204 No Content

    To delete a node_link, issue a DELETE request against `/links/self`.  A successful delete will return a 204 No Content
    response. Attempting to delete a node you do not own will result in a 403 Forbidden.

    ##Query Params

    *None*.

    #This Request/Response
    """
    permission_classes = (
        ContributorOrPublicForPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = CollectionNodeLinkSerializer
    view_category = 'nodes'
    view_name = 'node-pointer-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        node_link_lookup_url_kwarg = 'node_link_id'
        node_link = get_object_or_error(
            Pointer,
            self.kwargs[node_link_lookup_url_kwarg],
            'node link'
        )
        # May raise a permission denied
        self.kwargs['node_id'] = self.kwargs['collection_id']
        self.check_object_permissions(self.request, node_link)
        return node_link

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_node()
        pointer = self.get_object()
        try:
            node.rm_pointer(pointer, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise ValidationError(err.message)
        node.save()

class CollectionLinkedNodesRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, CollectionMixin):
    """ Relationship Endpoint for Collection -> Linked Node relationships

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
    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = LinkedNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'collections'
    view_name = 'collection-node-pointer-relationship'

    def get_object(self):
        collection = self.get_node(check_object_permissions=False)
        auth = get_user_auth(self.request)
        obj = {'data': [
            pointer for pointer in
            collection.nodes_pointer
            if not pointer.node.is_deleted and not pointer.node.is_collection and
            pointer.node.can_view(auth)
        ], 'self': collection}
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        auth = get_user_auth(self.request)
        current_pointers = {pointer.node._id: pointer for pointer in instance['data']}
        collection = instance['self']
        for val in data:
            if val['id'] in current_pointers:
                collection.rm_pointer(current_pointers[val['id']], auth)

    def create(self, *args, **kwargs):
        try:
            ret = super(CollectionLinkedNodesRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret
