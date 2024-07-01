from rest_framework import exceptions
from rest_framework import permissions

from api.base.exceptions import Gone
from api.base.utils import get_user_auth, assert_resource_type
from osf.models import Registration


class ResourcesPermission:
    '''Base permissions class for acting on Resources.

    To GET an Resource (when the method is available), the user must have `can_view` access
    to the proxy_object designated by the view (i.e. the Primary Registration).

    For all other methods, the user must have the permissions designated by the
    REQUIRED_PERMISSIONS dictionary for the Permission subclass

    Note: SchemaResponses for deleted parent resources should appear to be deleted,
    while access should be denied to SchemaResponses on withdrawn parent resources.
    '''
    acceptable_models = (Registration,)
    REQUIRED_PERMISSIONS = {}

    def has_permission(self, request, view):
        if request.method not in self.REQUIRED_PERMISSIONS.keys():
            raise exceptions.MethodNotAllowed(request.method)

        proxy_object = view.get_permissions_proxy()
        assert_resource_type(proxy_object, self.acceptable_models)
        if proxy_object.deleted:
            # Mimics get_object_or_error logic
            raise Gone
        if getattr(proxy_object, 'is_retracted', False):
            # Mimics behavior of ExcludeWithdrawals for Registration Resources
            return False

        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return proxy_object.is_public or proxy_object.can_view(auth)

        return proxy_object.has_permission(auth.user, self.REQUIRED_PERMISSIONS[request.method])


class ResourceListPermission(ResourcesPermission, permissions.BasePermission):
    '''Permissions for the top-level ResourceList endpoint.

    ResourceList only supports POST
    '''
    REQUIRED_PERMISSIONS = {'POST': 'write'}


class ResourceDetailPermission(ResourcesPermission, permissions.BasePermission):
    '''Permissions for the top-level ResourcesDetail endpoint.

    ResourcesDetail supports GET, PATCH, and DELETE methods.
    '''
    REQUIRED_PERMISSIONS = {'GET': None, 'PATCH': 'write', 'DELETE': 'write'}


class RegistrationResourceListPermission(ResourcesPermission, permissions.BasePermission):
    '''Permissions for the Registration's ResourceList relationship endpoint.

    RegistrationResourceList only supports GET
    '''
    REQUIRED_PERMISSIONS = {'GET': None}
