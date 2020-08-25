from rest_framework import permissions
from osf.models.oauth import ApiOAuth2Scope

class IsPublicScope(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, ApiOAuth2Scope), 'obj must be an ApiOAuth2Scope got {}'.format(obj)
        return obj.is_public
