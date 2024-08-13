from rest_framework import permissions

from api.base.utils import get_user_auth
from addons.wiki.models import WikiPage, WikiVersion


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiPage), f'obj must be a WikiPage, got {obj}'
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.node.is_public or obj.node.can_view(auth)
        return (
            obj.node.can_edit(auth)
            or obj.node.addons_wiki_node_settings.is_publicly_editable
        )

class ContributorOrPublicWikiVersion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiVersion), f'obj must be a WikiVersion, got {obj}'
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.wiki_page.node.is_public or obj.wiki_page.node.can_view(auth)
        return obj.wiki_page.node.can_edit(auth)


class ExcludeWithdrawals(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiPage), f'obj must be a WikiPage, got {obj}'
        node = obj.node
        if node and node.is_retracted:
            return False
        return True


class ExcludeWithdrawalsWikiVersion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiVersion), f'obj must be a WikiVersion, got {obj}'
        node = obj.wiki_page.node
        if node and node.is_retracted:
            return False
        return True
