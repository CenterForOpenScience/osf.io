from rest_framework import permissions


class IsPreprintMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='preprint_metrics').exists():
            return True
        return False
