from rest_framework import permissions
from api.scopes.serializers import Scope

class IsPublicScope(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, Scope), 'obj must be an Scope got {}'.format(obj)
        return obj.is_public
