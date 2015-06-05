from website.models import User
from rest_framework import permissions


class ReadOnlyOrCurrentUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, User), 'obj must be a User, got {}'.format(obj)
        request_user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj == request_user
