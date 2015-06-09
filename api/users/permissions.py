from website.models import OAuth2App
from rest_framework import permissions


class OwnerOnly(permissions.BasePermission):
    """User must be logged in, own the instance, and match the user ID in the URL"""

    # TODO: Write tests for basic, session, and oauth-based authentication
    def has_object_permission(self, request, view, obj):
        """Not applied to all members of a queryset"""
        assert isinstance(obj, OAuth2App), "obj must be an OAuth2App, got {}".format(obj)
        return (obj.owner._id == request.user._id)

    def has_permission(self, request, view):
        return (view.kwargs.get('user_id', '') == request.user._id)
