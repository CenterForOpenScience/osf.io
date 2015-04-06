from rest_framework import permissions

from framework.auth import Auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)
