from django.contrib.auth.models import AnonymousUser

from rest_framework.permissions import BasePermission


class IsCasLogin(BasePermission):
    """
    Allow access for CAS authentication request.
    """

    def has_permission(self, request, view):
        return request.user and not isinstance(request.user, AnonymousUser) and request.user.is_authenticated
