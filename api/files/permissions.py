from rest_framework import permissions

from framework.auth import Auth
from website.files.models import FileNode


def get_user_auth(request):
    user = request.user
    if user.is_anonymous():
        auth = Auth(None)
    else:
        auth = Auth(user)
    return auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, FileNode), 'obj must be a Node or Pointer, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.node.is_public or obj.node.can_view(auth)
        else:
            if not obj.node.can_edit(auth):
                return False

            return any(
                obj.checkout is None,
                obj.checkout == auth.user,
                obj.node.has_permission(auth.user, 'admin')
            )
