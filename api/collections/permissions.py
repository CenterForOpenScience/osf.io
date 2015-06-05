from website.models import Node
from rest_framework import permissions

class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
