# -*- coding: utf-8 -*-
from rest_framework import permissions

from website.models import NodeLog

from api.nodes.permissions import ContributorOrPublic


class ContributorOrPublicForLogs(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NodeLog), 'obj must be a NodeLog, got {}'.format(obj)
        return ContributorOrPublic().has_object_permission(request, view, obj.node)
