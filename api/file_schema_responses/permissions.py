from osf.models import FileSchemaResponse
from api.registration_schema_responses.permissions import SchemaResponseParentPermission

from rest_framework import exceptions
from rest_framework import permissions

from api.base.exceptions import Gone
from api.base.utils import get_user_auth, assert_resource_type


class FileSchemaResponseDetailPermission(SchemaResponseParentPermission):
    acceptable_models = (FileSchemaResponse,)
    REQUIRED_PERMISSIONS = {'PATCH': 'write'}

    def has_object_permission(self, request, view, obj):
        if request.method not in ['GET', *self.REQUIRED_PERMISSIONS.keys()]:
            raise exceptions.MethodNotAllowed(request.method)
        assert_resource_type(obj, self.acceptable_models)

        schema_response = self._get_schema_response(obj)
        file = schema_response.parent
        if file.deleted:
            raise Gone

        resource = file.target
        if resource.deleted:
            raise Gone

        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return True

        required_permission = self.REQUIRED_PERMISSIONS[request.method]
        if required_permission:
            return resource.has_permission(auth.user, required_permission)
        return True
