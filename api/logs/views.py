from modularodm import Q
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from website.models import Node, NodeLog

from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ODMFilterMixin
from api.base.utils import get_user_auth
from api.base import permissions as base_permissions
from api.logs.serializers import NodeLogSerializer
from api.nodes.serializers import NodeSerializer
from api.nodes.utils import get_visible_nodes_for_user

class LogList(generics.ListAPIView, ODMFilterMixin):
    """List of logs representing actions done on the OSF. *Read-only*.

    Paginated list of logs ordered by their `date`.

    On the front end, logs show record and show actions done on the OSF. The complete list of loggable actions (in the format {identifier}: {description}) is as follows:

    * 'node_created': A Node is created
    * 'node_forked': A Node is forked
    * 'node_removed': A Node is deleted
    * 'created_from': A Node is created using an existing Node as a template
    * 'pointer_created': A Pointer is created
    * 'pointer_forked': A Pointer is forked
    * 'pointer_removed': A Pointer is removed
    ---
    * 'made_public': A Node is made public
    * 'made_private': A Node is made private
    * 'tag_added': A tag is added to a Node
    * 'tag_removed': A tag is removed from a Node
    * 'edit_title': A Node's title is changed
    * 'edit_description': A Node's description is changed
    * 'updated_fields': One or more of a Node's fields are changed
    * 'external_ids_added': An external identifier is added to a Node (e.g. DOI, ARK)
    ---
    * 'contributor_added': A Contributor is added to a Node
    * 'contributor_removed': A Contributor is removed from a Node
    * 'contributors_reordered': A Contributor's position is a Node's biliography is changed
    * 'permissions_update': A Contributor's permissions on a Node are changed
    * 'made_contributor_visible': A Contributor is made bibliographically visible on a Node
    * 'made_contributor_invisible': A Contributor is made bibliographically invisible on a Node
    ---
    * 'wiki_updated': A Node's wiki is updated
    * 'wiki_deleted': A Node's wiki is deleted
    * 'wiki_renamed': A Node's wiki is renamed
    * 'made_wiki_public': A Node's wiki is made public
    * 'made_wiki_private': A Node's wiki is made private
    ---
    * 'addon_added': An add-on is linked to a Node
    * 'addon_removed': An add-on is unlinked from a Node
    * 'addon_file_moved': A File in a Node's linked add-on is moved
    * 'addon_file_copied': A File in a Node's linked add-on is copied
    * 'addon_file_renamed': A File in a Node's linked add-on is renamed
    * 'folder_created': A Folder is created in a Node's linked add-on
    * 'file_added': A File is added to a Node's linked add-on
    * 'file_updated': A File is updated on a Node's linked add-on
    * 'file_removed': A File is removed from a Node's linked add-on
    * 'file_restored': A File is restored in a Node's linked add-on
    ---
    * 'comment_added': A Comment is added to some item
    * 'comment_removed': A Comment is removed from some item
    * 'comment_updated': A Comment is updated on some item
    ---
    * 'embargo_initiated': An embargoed Registration is proposed on a Node
    * 'embargo_approved': A proposed Embargo of a Node is approved
    * 'embargo_cancelled': A proposed Embargo of a Node is cancelled
    * 'embargo_completed': A proposed Embargo of a Node is completed
    * 'retraction_initiated': A Retraction of a Registration is proposed
    * 'retraction_approved': A Retraction of a Registration is approved
    * 'retraction_cancelled': A Retraction of a Registration is cancelled
    * 'registration_initiated': A Registration of a Node is proposed
    * 'registration_approved': A proposed Registration is approved
    * 'registration_cancelled': A proposed Registration is cancelled
    ---
    * 'project_created': A Node is created (_deprecated_)
    * 'project_registered': A Node is registered (_deprecated_)
    * 'project_deleted': A Node is deleted (_deprecated_)

   ##Log Attributes

    OSF Log entities have the "logs" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        date           iso8601 timestamp      timestamp of Log creation
        action         string                 Log action (see list above)

    ##Relationships

    ###Nodes

    A list of all Nodes this Log is added to.

    ###User

    The user who performed the logged action.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    ##Query Params

    Logs may be filtered by their `action` and `date`.

    #This Request/Response

    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeLogSerializer
    ordering = ('-date', )  # default ordering

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        allowed_node_ids = Node.find(Q('is_public', 'eq', True)).get_keys()
        user = self.request.user
        if not user.is_anonymous():
            allowed_node_ids = [n._id for n in get_visible_nodes_for_user(user)]
        logs_query = Q('__backrefs.logged.node.logs', 'in', list(allowed_node_ids))
        return logs_query

    def get_queryset(self):
        return NodeLog.find(self.get_query_from_request())

class LogNodeList(generics.ListAPIView, ODMFilterMixin):
    """List of nodes that a given log is associated with. *Read-only*.

    Paginated list of nodes that the user contributes to.  Each resource contains the full representation of the node,
    meaning additional requests to an individual node's detail view are not necessary. If the user id in the path is the
    same as the logged-in user, all nodes will be visible.  Otherwise, you will only be able to see the other user's
    publicly-visible nodes.  The special user id `me` can be used to represent the currently logged-in user.

    ##Node Attributes

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
    )

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeSerializer
    order = ('-date', )

    def get_queryset(self):
        log = NodeLog.load(self.kwargs.get('log_id'))
        if not log:
            raise NotFound(
                detail='No log matching that log_id could be found.'
            )
        else:
            auth_user = get_user_auth(self.request)
            return [
                node for node in log.node__logged
                if node.can_view(auth_user)
            ]
