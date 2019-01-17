from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import NodeLog
from api.logs.permissions import (
    ContributorOrPublicForLogs
)

from api.base import permissions as base_permissions
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


class NodeLogDetail(JSONAPIBaseView, generics.RetrieveAPIView, LogMixin):
    """Details about a given Node Log. *Read-only*.

     On the front end, logs show record and show actions done on the GakuNin RDM. The complete list of loggable actions (in the format {identifier}: {description}) is as follows:

    * 'project_created': A Node is created
    * 'project_registered': A Node is registered
    * 'project_deleted': A Node is deleted
    * 'created_from': A Node is created using an existing Node as a template
    * 'pointer_created': A Pointer is created
    * 'pointer_forked': A Pointer is forked
    * 'pointer_removed': A Pointer is removed
    * 'node_removed': A component is deleted
    * 'node_forked': A Node is forked
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
    * 'contributors_reordered': A Contributor's position in a Node's bibliography is changed
    * 'permissions_updated': A Contributor's permissions on a Node are changed
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
    * 'node_authorized': An addon is authorized for a project
    * 'node_deauthorized': An addon is deauthorized for a project
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
    * 'retraction_initiated': A Withdrawal of a Registration is proposed
    * 'retraction_approved': A Withdrawal of a Registration is approved
    * 'retraction_cancelled': A Withdrawal of a Registration is cancelled
    * 'registration_initiated': A Registration of a Node is proposed
    * 'registration_approved': A proposed Registration is approved
    * 'registration_cancelled': A proposed Registration is cancelled
    ---
    * 'node_created': A Node is created (_deprecated_)

   ##Log Attributes

    <!--- Copied Attributes from LogList -->

    OSF Log entities have the "logs" `type`.

        name           type                   description
        ----------------------------------------------------------------------------
        date           iso8601 timestamp      timestamp of Log creation
        action         string                 Log action (see list above)

    ##Relationships

    ###Node

    The node this log belongs to.

    ###Original Node

    The node this log pertains to.

    ###User

    The user who performed the logged action.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    <!--- Copied Query Params from LogList -->

    Logs may be filtered by their `action` and `date`.

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
