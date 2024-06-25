from rest_framework import exceptions
from rest_framework import permissions

from api.base.utils import get_user_auth, assert_resource_type
from osf.models import BaseFileNode, Registration
from api.preprints.permissions import PreprintPublishedOrAdmin
from osf.utils.permissions import ADMIN
from osf.utils.workflows import DefaultStates
from api.base.exceptions import Gone

class CheckedOutOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, BaseFileNode), 'obj must be a BaseFileNode, got {}'.format(obj)

        if request.method in permissions.SAFE_METHODS:
            return True

        auth = get_user_auth(request)
        # Limited to osfstorage for the moment
        if obj.provider != 'osfstorage':
            return False
        return obj.checkout is None \
            or obj.checkout == auth.user \
            or obj.target.has_permission(auth.user, ADMIN)


class IsPreprintFile(PreprintPublishedOrAdmin):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, BaseFileNode), 'obj must be a BaseFileNode, got {}'.format(obj)
        if (hasattr(obj.target, 'primary_file') and obj.target.primary_file == obj):
            if request.method == 'DELETE' and obj.target.machine_state != DefaultStates.INITIAL.value:
                return False

            if obj.target.is_retracted and request.method in permissions.SAFE_METHODS:
                return obj.target.can_view_files(get_user_auth(request))

            # If object is a primary_file on a preprint, need PreprintPublishedOrAdmin permissions to view
            return super(IsPreprintFile, self).has_object_permission(request, view, obj.target)

        return True
    

class WithdrawnRegistrationPermission(permissions.BasePermission):
    acceptable_models = (Registration, )
    REQUIRED_PERMISSIONS = {}

    def has_permission(self, request, view):
        if request.method not in self.REQUIRED_PERMISSIONS.keys() and request.method not in permissions.SAFE_METHODS:
            raise exceptions.MethodNotAllowed(request.method)

        obj = view.get_object()
        return self.has_object_permission(request, view, obj)

    def has_object_permission(self, request, view, obj):
        if request.method not in ['GET', *self.REQUIRED_PERMISSIONS.keys()]:
            raise exceptions.MethodNotAllowed(request.method)
        assert isinstance(obj, BaseFileNode), 'obj must be a BaseFileNode, got {}'.format(obj)
        if not isinstance(obj.target, self.acceptable_models):
            return True
        assert_resource_type(obj.target, self.acceptable_models)

        target = obj.target
        if target.is_deleted:
            raise Gone
        if getattr(target, 'is_withdrawn', False):
            return False

        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return target.is_public or target.can_view(auth)

        required_permission = self.REQUIRED_PERMISSIONS.get(request.method)
        if required_permission:
            return target.has_permission(auth.user, required_permission)
        return True

class FileDetailPermission(WithdrawnRegistrationPermission, permissions.BasePermission):
    REQUIRED_PERMISSIONS = {'PATCH': 'write', 'DELETE': 'write'}
