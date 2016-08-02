from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.view_only_links.serializers import ViewOnlyLinkDetailSerializer

from website.models import PrivateLink


class ViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
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
        nodes                       array of node GUIDs     list of nodes which this view only link gives read-only access to


    ##Relationships

    ###Creator

    The user who created the view only link.

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
