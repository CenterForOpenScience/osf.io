from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.view_only_links.serializers import ViewOnlyLinkDetailSerializer

from website.models import Node, PrivateLink


class ViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Details about a specific view only link. *Read-only*.

    ###Permissions

    View only links are visible only to users that are administrators on all of the nodes which a view only link
    pertains to.

    ##Attributes

    OSF view only links entities have the "view-only-links" `type`.

        name                        type                    description
        ======================================================================================================
        name                        string                  name of the view only link
        anonymous                   boolean                 whether the view only link has anonymized contributors
        date_created                iso8601 timestamp       timestamp when the view only link was created
        key                         string                  the view only key


    ##Relationships

    ###Creator

    The user who created the view only link.

    ###Nodes

    The nodes which this view only link key gives read-only access to.

    ##Query Params

    *None*.

    #This Request/Response

    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = ViewOnlyLinkDetailSerializer

    view_category = 'view-only-links'
    view_name = 'view-only-link-detail'

    def get_object(self):
        link_id = self.kwargs['link_id']
        view_only_link = PrivateLink.load(link_id)
        user = get_user_auth(self.request).user

        for node in view_only_link.nodes:
            if not node.has_permission(user, 'admin'):
                raise PermissionDenied

        if not view_only_link:
            raise NotFound

        return view_only_link


class ViewOnlyLinkNodes(JSONAPIBaseView, generics.ListAPIView):
    """
    Details about the nodes which this view only link key gives read-only access to. *Read-only*.

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
            collection                      boolean            is this a collection? (always false - may be deprecated in future versions)
            node_license                    object             details of the license applied to the node
                year                        string             date range of the license
                copyright_holders           array of strings   holders of the applied license

    """

    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeSerializer

    view_category = 'view-only-links'
    view_name = 'view-only-link-nodes'

    def get_serializer_class(self):
        view_only_link = PrivateLink.load(self.kwargs['link_id'])
        node = Node.load(view_only_link.nodes[0])
        if node.is_registration:
            return RegistrationSerializer
        return NodeSerializer

    def get_queryset(self):
        link_id = self.kwargs['link_id']
        view_only_link = PrivateLink.load(link_id)

        return [
            Node.load(node) for node in
            view_only_link.nodes
        ]
