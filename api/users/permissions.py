from osf.models import OSFUser
from rest_framework import permissions


class ReadOnlyOrCurrentUser(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged in user,
    and allow non-safe actions if so.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, OSFUser), 'obj must be a User, got {}'.format(obj)
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
        assert isinstance(requested_user, OSFUser), 'obj must be a User, got {}'.format(requested_user)
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
        assert isinstance(claimed_user, OSFUser), 'obj must be a User, got {}'.format(claimed_user)
        return not claimed_user.is_registered

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, OSFUser), 'obj must be a User, got {}'.format(obj)
        return not obj.is_registered
