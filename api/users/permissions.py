from website.models import User
from rest_framework import permissions

from framework.auth import Auth


def get_user_auth(request):
    user = request.user
    if user.is_anonymous():
        auth = Auth(None)
    else:
        auth = Auth(user)
    return auth


class AuthorizedUserOrPublic(permissions.BasePermission):

    def has_user_permission(self, request, view, obj):
        assert isinstance(obj, User), 'obj must be a User, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public
        else:
            return obj.can_edit(auth)
