# -*- coding: utf-8 -*-
from rest_framework import permissions
from addons.wiki.models import WikiVersion

from api.base.utils import get_user_auth


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiVersion), 'obj must be a WikiVersion, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.wiki_page.node.is_public or obj.wiki_page.node.can_view(auth)
        else:
            return obj.wiki_page.node.can_edit(auth)


class ExcludeWithdrawals(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        node = obj.wiki_page.node
        if node and node.is_retracted:
            return False
        return True
