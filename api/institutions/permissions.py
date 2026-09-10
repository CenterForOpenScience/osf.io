import waffle
from rest_framework import exceptions, permissions

from api.base.utils import get_user_auth
from osf import features


class UserIsAffiliated(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        user = get_user_auth(request).user

        if request.method in permissions.SAFE_METHODS or request.method == 'DELETE':
            return True
        else:
            return user.is_affiliated_with_institution(obj['self'])


class InstitutionNodesDeleteNotAllowed(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.method == 'DELETE' and waffle.flag_is_active(request, features.PROJECT_READ_ONLY):
            raise exceptions.MethodNotAllowed(request.method, detail='This action is no longer available. Contact support if you have any questions.')
        return True
