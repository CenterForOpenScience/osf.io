from rest_framework import permissions

from website.models import ApiOAuth2PersonalToken


class OwnerOnly(permissions.BasePermission):
    """User must be logged in and be the owner of the instance"""

    # TODO: Write tests for basic, and session authentication
    def has_object_permission(self, request, view, obj):
        """Not applied to all members of a queryset"""
        assert isinstance(obj, ApiOAuth2PersonalToken), "obj must be an ApiOAuth2PersonalToken, got {}".format(obj)
        return (obj.owner._id == request.user._id)
