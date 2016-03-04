# -*- coding: utf-8 -*-
from rest_framework import permissions

from website.models import Node, NodeLog

from api.nodes.permissions import ContributorOrPublic
from api.base.utils import get_object_or_error


class ContributorOrPublicForLogs(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (NodeLog)), 'obj must be a NodeLog, got {}'.format(obj)

        if obj._backrefs.get('logged'):
            for node_id in obj._backrefs['logged']['node']['logs']:
                node = get_object_or_error(Node, node_id, display_name='node')
                if ContributorOrPublic().has_object_permission(request, view, node):
                    return True

        if getattr(obj, 'node'):
            if ContributorOrPublic().has_object_permission(request, view, obj.node):
                return True

        return False
