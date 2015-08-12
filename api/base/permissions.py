"""
Permissions classes intended to be shared across all types of API endpoints
"""

from rest_framework import permissions

class InternalOnly(permissions.BasePermission):
    """
    This route is intended for internal (OSF) consumption only, and access should be denied for OAuth2 requests
    """
    def has_permission(self, request, view):
        """Identify OAuth consumers based on whether request.auth is set (eg whether the authentication class
        returns two values from the authenticate() method"""
        return request.auth is None  # TODO: Improve this check as more token data is stored.
