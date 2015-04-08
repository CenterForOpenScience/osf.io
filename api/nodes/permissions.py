from website.models import Node
from rest_framework import permissions

from framework.auth import Auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node'
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)

class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
