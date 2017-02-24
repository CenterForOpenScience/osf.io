from rest_framework.permissions import BasePermission


class IsCasAuthentication(BasePermission):
    """
    Allow access for CAS authentication request.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated()
