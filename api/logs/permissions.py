from rest_framework import permissions

from osf.models import NodeLog

from api.nodes.permissions import ContributorOrPublic


class ContributorOrPublicForLogs(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NodeLog), f'obj must be a NodeLog, got {obj}'
        return ContributorOrPublic().has_object_permission(request, view, obj.node)
