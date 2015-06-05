from website.models import Node, Pointer
from rest_framework import permissions

from framework.auth import Auth


def get_user_auth(request):
    user = request.user
    if user.is_anonymous():
        auth = Auth(None)
    else:
        auth = Auth(user)
    return auth


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
