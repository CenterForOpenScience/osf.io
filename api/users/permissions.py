from website.models import User
from rest_framework import permissions


class ReadOnlyOrCurrentUser(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged in user,
    and allow non-safe actions if so.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, User), 'obj must be a User, got {}'.format(obj)
        request_user = request.user
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return obj == request_user

class CurrentUser(permissions.BasePermission):
    """ Check to see if the request is coming from the currently logged user
    """

    def has_permission(self, request, view):
        # import ipdb; ipdb.set_trace()
        requested_user = view.get_user()
        assert isinstance(requested_user, User), 'obj must be a User, got {}'.format(requested_user)
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
