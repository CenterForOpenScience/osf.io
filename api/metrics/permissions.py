from rest_framework import permissions
from api.base.utils import get_user_auth

from osf.models import Institution


class IsPreprintMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='preprint_metrics').exists():
            return True
        return False

class IsInstitutionalMetricsUser(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if type(obj) != Institution:
            obj = obj.institution
        if not auth.user:
            return False
        if auth.user.has_perm('view_institutional_metrics', obj):
            return True
        return False

    def has_permission(self, request, view):
        institution = view.get_institution()
        return self.has_object_permission(request, view, institution)
