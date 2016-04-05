from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from modularodm import Q
from framework.auth.core import User
from framework.auth.oauth_scopes import CoreScopes

from website.models import NodeLog
from api.logs.permissions import (
    ContributorOrPublicForLogs
)

from api.base.filters import ODMFilterMixin
from api.base.utils import get_user_auth
from api.base import permissions as base_permissions
from api.nodes.serializers import NodeSerializer
from api.users.serializers import UserSerializer
from api.logs.serializers import NodeLogSerializer
from api.base.views import JSONAPIBaseView


class LogMixin(object):
    """
    Mixin with convenience method get_log
    """

    def get_log(self):
        log = NodeLog.load(self.kwargs.get('log_id'))
        if not log:
            raise NotFound(
                detail='No log matching that log_id could be found.'
            )

        self.check_object_permissions(self.request, log)
        return log


class LogNodeList(JSONAPIBaseView, generics.ListAPIView, LogMixin, ODMFilterMixin):
    """List of nodes that a given log is associated with. *Read-only*.

    Paginated list of nodes that the user contributes to.  Each resource contains the full representation of the node,
    meaning additional requests to an individual node's detail view are not necessary. If the user id in the path is the
    same as the logged-in user, all nodes will be visible.  Otherwise, you will only be able to see the other user's
    publicly-visible nodes.  The special user id `me` can be used to represent the currently logged-in user.

    ##Node Attributes

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
        registration   boolean            has this project been registered?
        collection     boolean            is this node a collection of other nodes?
        public         boolean            has this node been made publicly-visible?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, or `tags`.  `title`,
    `description`, and `category` are string fields and will be filtered using simple substring matching.  `public` and
    `registration` are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note
    that quoting `true` or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicForLogs
    )

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeSerializer
    view_category = 'logs'
    view_name = 'log-nodes'
    order = ('-date', )

    def get_queryset(self):
        log = self.get_log()
        auth_user = get_user_auth(self.request)
        return [
            node for node in log.node__logged
            if node.can_view(auth_user) and not node.is_deleted and not node.is_registration
        ]


class NodeLogDetail(JSONAPIBaseView, generics.RetrieveAPIView, LogMixin):
    """List of nodes that a given log is associated with. *Read-only*.

    Paginated list of nodes that the user contributes to.  Each resource contains the full representation of the node,
    meaning additional requests to an individual node's detail view are not necessary. If the user id in the path is the
    same as the logged-in user, all nodes will be visible.  Otherwise, you will only be able to see the other user's
    publicly-visible nodes.  The special user id `me` can be used to represent the currently logged-in user.

    Note that if an anonymous view_only key is being used, the user relationship will not be exposed.

    ##Node Attributes

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
        registration   boolean            has this project been registered?
        collection     boolean            is this node a collection of other nodes?
        public         boolean            has this node been made publicly-visible?

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    <!--- Copied Query Params from NodeList -->

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, or `tags`.  `title`,
    `description`, and `category` are string fields and will be filtered using simple substring matching.  `public` and
    `registration` are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note
    that quoting `true` or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicForLogs
    )

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeLogSerializer
    view_category = 'logs'
    view_name = 'log-detail'

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        log = self.get_log()
        return log

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        pass


class NodeLogContributors(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin, LogMixin):
    """List of contributors that a given log is associated with. *Read-only*.

    Paginated list of users that were associated with a contributor log action. For example, if a log action was `contributor_added`,
    the new contributors' names would be found at this endpoint. If the relevant log had nothing to do with contributors,
    an empty list would be returned. Each resource contains the full representation of the user, meaning additional requests
    to an individual user's detail view are not necessary.

    ##User Attributes

    <!--- Copied Attributes from UserDetail -->

    OSF User entities have the "users" `type`.

        name               type               description
        ========================================================================================
        full_name          string             full name of the user; used for display
        given_name         string             given name of the user; for bibliographic citations
        middle_names       string             middle name of user; for bibliographic citations
        family_name        string             family name of user; for bibliographic citations
        suffix             string             suffix of user's name for bibliographic citations
        date_registered    iso8601 timestamp  timestamp when the user's account was created


    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    <!--- Copied Query Params from UserList -->

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Users may be filtered by their `id`, `full_name`, `given_name`, `middle_names`, or `family_name`.

    + `profile_image_size=<Int>` -- Modifies `/links/profile_image_url` of the user entities so that it points to
    the user's profile image scaled to the given size in pixels.  If left blank, the size depends on the image provider.

    #This Request/Response
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublicForLogs
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = UserSerializer

    view_category = 'logs'
    view_name = 'log-contributors'

    # overrides ListAPIView
    def get_queryset(self):
        log = self.get_log()
        associated_contrib_ids = log.params.get('contributors')
        if associated_contrib_ids is None:
            return []
        associated_users = User.find(Q('_id', 'in', associated_contrib_ids))
        return associated_users
