from rest_framework import permissions
from api.base.utils import assert_resource_type
from osf.models import Institution


class IsPreprintMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='preprint_metrics').exists():
            return True
        return False


class IsRawMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='raw_es6').exists():
            return True
        return False


class IsRegistriesModerationMetricsUser(permissions.BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if user.system_tags.filter(name='registries_moderation_metrics').exists():
            return True
        return False


class IsInstitutionalMetricsUser(permissions.BasePermission):

    acceptable_models = (Institution, )

    def has_object_permission(self, request, view, obj):
        user = request.user
        assert_resource_type(obj, self.acceptable_models)
        if not user:
            return False
        if user.has_perm('view_institutional_metrics', obj):
            return True
        return False

    def has_permission(self, request, view):
        institution = view.get_institution()
        return self.has_object_permission(request, view, institution)
