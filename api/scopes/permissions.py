from rest_framework import permissions
from osf.models.oauth import ApiOAuth2Scope

class IsPublicScope(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, ApiOAuth2Scope), f'obj must be an ApiOAuth2Scope got {obj}'
        return obj.is_public
