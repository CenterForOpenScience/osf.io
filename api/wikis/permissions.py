# -*- coding: utf-8 -*-
from rest_framework import exceptions
from rest_framework import permissions

from api.base.utils import get_user_auth
from addons.wiki.models import WikiPage, WikiVersion
from osf.models import AbstractNode


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiPage), 'obj must be a WikiPage, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.node.is_public or obj.node.can_view(auth)
        return (
            obj.node.can_edit(auth)
            or obj.node.addons_wiki_node_settings.is_publicly_editable
        )

class ContributorOrPublicWikiVersion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiVersion), 'obj must be a WikiVersion, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.wiki_page.node.is_public or obj.wiki_page.node.can_view(auth)
        return obj.wiki_page.node.can_edit(auth)


class ExcludeWithdrawals(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiPage), 'obj must be a WikiPage, got {}'.format(obj)
        node = obj.node
        if node and node.is_retracted:
            return False
        return True


class ExcludeWithdrawalsWikiVersion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, WikiVersion), 'obj must be a WikiVersion, got {}'.format(obj)
        node = obj.wiki_page.node
        if node and node.is_retracted:
            return False
        return True


class IsEnabled(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (WikiPage, WikiVersion, AbstractNode)), 'obj must be a WikiPage, WikiVersion, or AbstractNode, got {}'.format(obj)
        if isinstance(obj, WikiPage):
            node = obj.node
        elif isinstance(obj, WikiVersion):
            node = obj.wiki_page.node
        else:
            node = obj
        if node.addons_wiki_node_settings.deleted:
            raise exceptions.NotFound(detail='The wiki for this node has been disabled.')
        return True
