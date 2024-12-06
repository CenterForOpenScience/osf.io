from rest_framework import permissions, exceptions

from osf.models import OSFUser, Institution
from osf.models.user_message import MessageTypes


class ReadOnlyOrCurrentUser(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged in user,
    and allow non-safe actions if so.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, OSFUser), f'obj must be a User, got {obj}'
        request_user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj == request_user

class CurrentUser(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged user
    """

    def has_permission(self, request, view):
        requested_user = view.get_user()
        assert isinstance(requested_user, OSFUser), f'obj must be a User, got {requested_user}'
        return requested_user == request.user

class ReadOnlyOrCurrentUserRelationship(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged in user,
    and allow non-safe actions if so.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        request_user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj['self']._id == request_user._id

class ClaimUserPermission(permissions.BasePermission):
    """ Allows anyone to attempt to claim an unregistered user.
    Allows no one to attempt to claim a registered user.
    """
    def has_permission(self, request, view):
        claimed_user = view.get_user(check_permissions=False)
        assert isinstance(claimed_user, OSFUser), f'obj must be a User, got {claimed_user}'
        return not claimed_user.is_registered

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, OSFUser), f'obj must be a User, got {obj}'
        return not obj.is_registered


class UserMessagePermissions(permissions.BasePermission):
    """
    Custom permission to allow only institutional admins to create certain types of UserMessages.
    """
    def has_permission(self, request, view) -> bool:
        """
        Validate if the user has permission to perform the requested action.
        Args:
            request: The HTTP request.
            view: The view handling the request.
        Returns:
            bool: True if the user has the required permission, False otherwise.
        """
        user = request.user
        if not user or user.is_anonymous:
            return False

        message_type = request.data.get('message_type')
        if message_type == MessageTypes.INSTITUTIONAL_REQUEST:
            return self._validate_institutional_request(request, user)

        return False

    def _validate_institutional_request(self, request, user: OSFUser) -> bool:
        """
        Validate the user's permissions for creating an `INSTITUTIONAL_REQUEST` message.
        Args:
            request: The HTTP request containing the institution ID.
            user: The user making the request.
        Returns:
            bool: True if the user has the required permission.
        """
        institution_id = request.data.get('institution')
        if not institution_id:
            raise exceptions.ValidationError({'institution': 'Institution ID is required.'})

        institution = self._get_institution(institution_id)

        if not user.is_institutional_admin(institution):
            raise exceptions.PermissionDenied('You are not an admin of the specified institution.')

        return True

    def _get_institution(self, institution_id: str) -> Institution:
        """
        Retrieve the institution by its ID.
        Args:
            institution_id (str): The ID of the institution.
        Returns:
            Institution: The retrieved institution.
        """
        try:
            return Institution.objects.get(_id=institution_id)
        except Institution.DoesNotExist:
            raise exceptions.ValidationError({'institution': 'Specified institution does not exist.'})
