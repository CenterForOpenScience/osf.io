from rest_framework import permissions

from website.models import ApiOAuth2Application


class OwnerOnly(permissions.BasePermission):
    """User must be logged in and be the owner of the instance"""

    # TODO: Write tests for basic, session, and oauth-based authentication
    def has_object_permission(self, request, view, obj):
        """Not applied to all members of a queryset"""
        assert isinstance(obj, ApiOAuth2Application), "obj must be an ApiOAuth2Application, got {}".format(obj)
        return (obj.owner._id == request.user._id)
