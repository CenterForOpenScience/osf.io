from rest_framework import generics, permissions as drf_permissions


from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from website.project.model import Q, Node
from api.base import permissions as base_permissions

from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer
)
from api.base.utils import get_object_or_error

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
    has access.  Registrations share many of the same fields as nodes.
    """

    """Nodes that represent projects and components. *Writeable*.

    Paginated list of nodes ordered by their `date_modified`.  Each resource contains the full representation of the
    registration, meaning additional requests to an individual registrations's detail view are not necessary.

    <!--- Copied Spiel from NodeDetail -->

    ##Registration Attributes

    <!--- Copied Attributes from NodeDetail -->

    OSF Node entities have the "nodes" `type`.

        name           type               description
        ---------------------------------------------------------------------------------
        title          string             title of project or component
        description    string             description of the node
        category       string             node category, must be one of the allowed values
        date_created   iso8601 timestamp  timestamp that the node was created
        date_modified  iso8601 timestamp  timestamp when the node was last updated
        tags           array of strings   list of tags that describe the node
        registration   boolean            has this project been registered?
        collection     boolean            is this node a collection of other nodes?
        dashboard      boolean            is this node visible on the user dashboard?
        public         boolean            has this node been made publicly-visible?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ###Creating New Nodes

        Method:        POST
        URL:           links.self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "registrations", # required
                           "attributes": {
                             "title":       {title},          # required
                             "category":    {category},       # required
                             "description": {description},    # optional
                             "tags":        [{tag1}, {tag2}], # optional
                             "public":      true|false        # optional
                           }
                         }
                       }
        Success:       201 CREATED + node representation

    New nodes are created by issuing a POST request to this endpoint.  The `title` and `category` fields are
    mandatory. `category` must be one of the [permitted node categories](/v2/#osf-node-categories).  `public` defaults
    to false.  All other fields not listed above will be ignored.  If the node creation is successful the API will
    return a 201 response with the respresentation of the new node in the body.  For the new node's canonical URL, see
    the `links.self` field of the response.

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
    """Details about a given node (project or component). *Writeable*.

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

        name           type               description
        ---------------------------------------------------------------------------------
        title          string             title of project or component
        description    string             description of the node
        category       string             node category, must be one of the allowed values
        date_created   iso8601 timestamp  timestamp that the node was created
        date_modified  iso8601 timestamp  timestamp when the node was last updated
        tags           array of strings   list of tags that describe the node
        registration   boolean            has this project been registered?
        collection     boolean            is this node a collection of other nodes?
        dashboard      boolean            is this node visible on the user dashboard?
        public         boolean            has this node been made publicly-visible?

    ##Relationships

    ###Children

    List of nodes that are children of this node.  New child nodes may be added through this endpoint.

    ###Contributors

    List of users who are contributors to this node.  Contributors may have "read", "write", or "admin" permissions.  A
    node must always have at least one "admin" contributor.  Contributors may be added via this endpoint.

    ###Files

    List of top-level folders (actually cloud-storage providers) associated with this node. This is the starting point
    for accessing the actual files stored within this node.

    ###Parent

    If this node is a child node of another node, the parent's canonical endpoint will be available in the
    `parent.links.self.href` key.  Otherwise, it will be null.

    ##Links

        self:  the canonical api endpoint of this node
        html:  this node's page on the OSF website

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           links.self
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

    To update a node, issue either a PUT or a PATCH request against the `links.self` URL.  The `title` and `category`
    fields are mandatory if you PUT and optional if you PATCH.  The `tags` parameter must be an array of strings.
    Non-string values will be accepted and stringified, but we make no promises about the stringification output.  So
    don't do that.

    ###Delete

        Method:   DELETE
        URL:      links.self
        Params:   <none>
        Success:  204 No Content

    To delete a node, issue a DELETE request against `links.self`.  A successful delete will return a 204 No Content
    response. Attempting to delete a node you do not own will result in a 403 Forbidden.

    ##Query Params

    *None*.

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
