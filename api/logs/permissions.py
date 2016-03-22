# -*- coding: utf-8 -*-
from rest_framework import permissions

from website.models import Node, NodeLog

from api.nodes.permissions import ContributorOrPublic


class ContributorOrPublicForLogs(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (NodeLog)), 'obj must be a NodeLog, got {}'.format(obj)

        if obj._backrefs.get('logged'):
            for node_id in obj._backrefs['logged']['node']['logs']:
                node = Node.load(node_id)
                if ContributorOrPublic().has_object_permission(request, view, node):
                    return True

        if getattr(obj, 'node'):
            return ContributorOrPublic().has_object_permission(request, view, obj.node)
        return False
