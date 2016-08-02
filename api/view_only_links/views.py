from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.view_only_links.serializers import ViewOnlyLinkDetailSerializer

from website.models import PrivateLink


class ViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    """
    Document pls.
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
