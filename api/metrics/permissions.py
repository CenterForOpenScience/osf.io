from rest_framework import permissions
from api.base.utils import get_user_auth


class IsPreprintMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='preprint_metrics').exists():
            return True
        return False

class IsInstitutionalMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        institution = view.get_institution()
        return self.has_object_permission(request, view, institution)

    def has_object_permission(self, request, view, obj):
        user = get_user_auth(request).user
        if user and user.has_perm('view_institutional_metrics', obj):
            return True
        return False
