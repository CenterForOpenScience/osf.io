import io

from rest_framework import exceptions
from rest_framework import permissions

from api.base.exceptions import Gone
from api.base.utils import get_user_auth, assert_resource_type, get_object_or_error
from api.base.parsers import JSONSchemaParser

from osf.models import Registration, SchemaResponse
from osf.utils.workflows import ApprovalStates


class SchemaResponseDetailPermission(permissions.BasePermission):
    '''
    Permissions for top-level `schema_response` detail endpoints.

    To GET a SchemaResponse, one of three conditions must be met:
      *  The user must have "read" permissions on the parent resource
      *  The user must be a moderator on the parent resource's Provider and the
         SchemaResponse must be in an APPROVED or PENDING_MODERATION state
      *  The SchemaResponse must be APPROVED and the parent resource must be public

    To PATCH to a SchemaResponse, a user must have "write" permissions on the parent resource.

    To DELETE a SchemaResponse, a user must have "admin" permissions on the parent resource.

    Note: SchemaResponses on deleted parent resources should appear to be deleted, while
    access should be denied to SchemaResponses on withdrawn parent resources.
    '''
    acceptable_models = (SchemaResponse, )

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        parent = obj.parent

        if parent.deleted:
            # Mimics get_object_or_error logic
            raise Gone
        if parent.is_retracted:
            # Mimics behavior of ExcludeWithdrawals
            return False

        if request.method in permissions.SAFE_METHODS:
            return (
                (parent.is_public and obj.state is ApprovalStates.APPROVED)
                or (
                    auth.user is not None
                    and parent.is_moderated
                    and obj.state in [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]
                    and auth.user.has_perm('view_submissions', parent.provider)
                )
                or parent.has_permission(auth.user, 'read')
            )
        elif request.method == 'PATCH':
            return parent.has_permission(auth.user, 'write')
        elif request.method == 'DELETE':
            return parent.has_permission(auth.user, 'admin')
        else:
            raise exceptions.MethodNotAllowed(request.method)

    def has_permission(self, request, view):
        obj = view.get_object()
        return self.has_object_permission(request, view, obj)


class RegistrationSchemaResponseListPermission(permissions.BasePermission):
    '''
    Permissions for the registration relationship view for schema responses.

    To GET a registration's SchemaResponses, the registration must be visible to the user.
    '''
    acceptable_models = (Registration, )

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
    acceptable_models = (Registration, )

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


class SchemaResponseActionPermission(permissions.BasePermission):
    '''
    Permissions for `schema_responses/<schema_responses>/actions/` list endpoints.

    GET permissions for SchemaResponseActionList and SchemaResponseActionDetail should mimic
    the permissions for SchemaResponseDetail

    POST permissions are state-sensitive and should be enforced by the model
    '''

    def has_object_permission(self, request, view, obj):
        if request.method not in permissions.SAFE_METHODS:
            raise exceptions.MethodNotAllowed(request.method)

        parent = obj.parent
        if parent.deleted:
            # Mimics get_object_or_error logic
            raise Gone
        if parent.is_retracted:
            # Mimics behavior of ExcludeWithdrawals
            return False
        if parent.deleted:
            raise Gone

        auth = get_user_auth(request)
        return (
            (parent.is_public and obj.state is ApprovalStates.APPROVED)
            or (
                auth.user is not None
                and parent.is_moderated
                and obj.state in [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]
                and auth.user.has_perm('view_submissions', parent.provider)
            )
            or parent.has_permission(auth.user, 'read')
        )

    def has_permission(self, request, view):
        if request.method == 'POST':
            return True  # these permissions are checked by the SchemaResponse state machine.
        schema_response = view.get_base_resource()
        return self.has_object_permission(request, view, schema_response)
