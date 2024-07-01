import io

from rest_framework import exceptions
from rest_framework import permissions

from api.base.exceptions import Gone
from api.base.utils import get_user_auth, assert_resource_type, get_object_or_error
from api.base.parsers import JSONSchemaParser

from osf.models import Registration, SchemaResponse, SchemaResponseAction
from osf.utils.workflows import ApprovalStates


MODERATOR_VISIBLE_STATES = [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]


class SchemaResponseParentPermission:
    '''Base permissions class for an individual SchemaResponse and subpaths

    To GET a SchemaResponse (or a subpath), one of three conditions must be met:
      *  The user must have "read" permissions on the parent resource
      *  The user must be a moderator on the parent resource's Provider and the
         SchemaResponse must be in an APPROVED or PENDING_MODERATION state
      *  The SchemaResponse must be APPROVED and the parent resource must be public

    For DELETE/PATCH/POST/PUT, the required permission should be added in the
    REQUIRED_PERMISSIONS dictionary. No entry means the method is not allowed,
    None means no permission is required.

    Note: SchemaResponses for deleted parent resources should appear to be deleted,
    while access should be denied to SchemaResponses on withdrawn parent resources.
    '''
    acceptable_models = (SchemaResponse,)
    REQUIRED_PERMISSIONS = {}

    def _get_schema_response(self, obj):
        '''Get the SchemaResponse from the result of a get_object call on the view.'''
        return obj

    def has_permission(self, request, view):
        obj = view.get_object()
        return self.has_object_permission(request, view, obj)

    def has_object_permission(self, request, view, obj):
        if request.method not in ['GET', *self.REQUIRED_PERMISSIONS.keys()]:
            raise exceptions.MethodNotAllowed(request.method)
        assert_resource_type(obj, self.acceptable_models)

        schema_response = self._get_schema_response(obj)
        parent = schema_response.parent
        if parent.deleted:
            # Mimics get_object_or_error logic
            raise Gone
        if parent.is_retracted:
            # Mimics behavior of ExcludeWithdrawals
            return False

        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return (
                (parent.is_public and schema_response.state is ApprovalStates.APPROVED)
                or (
                    auth.user is not None
                    and parent.is_moderated
                    and schema_response.state in MODERATOR_VISIBLE_STATES
                    and auth.user.has_perm('view_submissions', parent.provider)
                )
                or parent.has_permission(auth.user, 'read')
            )

        required_permission = self.REQUIRED_PERMISSIONS[request.method]
        if required_permission:
            return parent.has_permission(auth.user, required_permission)
        return True


class SchemaResponseDetailPermission(SchemaResponseParentPermission, permissions.BasePermission):
    '''
    Permissions for top-level `schema_response` detail endpoints.

    See SchemaResponseParentPermission for GET permission requirements

    To PATCH to a SchemaResponse, a user must have "write" permissions on the parent resource.

    To DELETE a SchemaResponse, a user must have "admin" permissions on the parent resource.
    '''
    REQUIRED_PERMISSIONS = {'DELETE': 'admin', 'PATCH': 'write'}


class RegistrationSchemaResponseListPermission(permissions.BasePermission):
    '''
    Permissions for the registration relationship view for schema responses.

    To GET a registration's SchemaResponses, the registration must be visible to the user.
    '''
    acceptable_models = (Registration,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            raise exceptions.MethodNotAllowed(request.method)

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.get_object())


class SchemaResponseListPermission(permissions.BasePermission):
    '''
    Permissions for top-level `schema_responses` list endpoints.

    All users can GET the list of schema responses

    To POST a SchemaResponse, the user must have "admin" permissions on the
    specified parent resource.
    '''
    acceptable_models = (Registration,)

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        elif request.method == 'POST':
            # Validate json before using id to check for permissions
            request_json = JSONSchemaParser().parse(
                io.BytesIO(request.body),
                parser_context={
                    'request': request,
                    'json_schema': view.create_payload_schema,
                },
            )
            obj = get_object_or_error(
                Registration,
                query_or_pk=request_json['data']['relationships']['registration']['data']['id'],
                request=request,
            )

            return self.has_object_permission(request, view, obj)
        else:
            raise exceptions.MethodNotAllowed(request.method)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        return obj.has_permission(auth.user, 'admin')


class SchemaResponseActionListPermission(SchemaResponseParentPermission, permissions.BasePermission):
    '''
    Permissions for `schema_responses/<schema_responses>/actions/` list endpoints.

    See SchemaResponseParentPermission for GET permission requirements

    POST permissions are state-sensitive and should be enforced by the model
    '''

    REQUIRED_PERMISSIONS = {'POST': None}


class SchemaResponseActionDetailPermission(SchemaResponseParentPermission, permissions.BasePermission):
    '''
    Permissions for `schema_responses/<schema_responses>/actions/` list endpoints.

    See SchemaResponseParentPermission for GET permission requirements

    No additional methods supported
    '''

    acceptable_models = (SchemaResponseAction,)

    def _get_schema_response(self, obj):
        return obj.target
