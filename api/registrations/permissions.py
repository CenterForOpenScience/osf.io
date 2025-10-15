from guardian.shortcuts import get_perms
from rest_framework import permissions

from api.base.utils import get_user_auth

class ContributorOrModerator(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        is_admin = obj.provider.get_group('admin').user_set.filter(id=auth.user.id).exists()
        is_moderator = obj.provider.get_group('moderator').user_set.filter(id=auth.user.id).exists()

        return obj.is_admin_contributor(auth.user) or is_moderator or is_admin


class ContributorOrModeratorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)

        # If a user has perms on the provider, they must be a moderator or admin
        is_moderator = bool(get_perms(auth.user, obj.provider)) if obj.provider else False
        return obj.can_edit(auth=auth) or is_moderator
