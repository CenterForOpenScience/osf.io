# -*- coding: utf-8 -*-
from rest_framework import permissions
from website.addons.wiki.model import NodeWikiPage

from api.base.utils import get_user_auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NodeWikiPage), 'obj must be a NodeWikiPage, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.node.is_public or obj.node.can_view(auth)
        else:
            return obj.node.can_edit(auth)


class ExcludeWithdrawals(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        node = obj.node
        if node and node.is_retracted:
            return False
        return True
