# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from website.models import Node, Pointer, User, Institution, DraftRegistration
from website.util import permissions as osf_permissions

from api.base.utils import get_user_auth
from api.registrations.utils import is_prereg_admin


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, Pointer)), 'obj must be a Node or Pointer, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)


class IsAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, DraftRegistration)), 'obj must be a Node or a Draft Registration, got {}'.format(obj)
        auth = get_user_auth(request)
        node = Node.load(request.parser_context['kwargs']['node_id'])
        return node.has_permission(auth.user, osf_permissions.ADMIN)


class IsAdminOrReviewer(permissions.BasePermission):
    """
    Prereg admins can update draft registrations.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, DraftRegistration)), 'obj must be a Node or a Draft Registration, got {}'.format(obj)
        auth = get_user_auth(request)
        node = Node.load(request.parser_context['kwargs']['node_id'])
        if request.method != 'DELETE' and is_prereg_admin(auth.user):
            return True
        return node.has_permission(auth.user, osf_permissions.ADMIN)


class AdminOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, User, Institution, DraftRegistration)), 'obj must be a Node, User, Institution, or Draft Registration, got {}'.format(obj)
        auth = get_user_auth(request)
        node = Node.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ExcludeRetractions(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        context = request.parser_context['kwargs']
        node = Node.load(context[view.node_lookup_url_kwarg])
        if node.is_retracted:
            return False
        return True


class ContributorDetailPermissions(permissions.BasePermission):
    """Permissions for contributor detail page."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, User)), 'obj must be User or Node, got {}'.format(obj)
        auth = get_user_auth(request)
        context = request.parser_context['kwargs']
        node = Node.load(context[view.node_lookup_url_kwarg])
        user = User.load(context['user_id'])
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        elif request.method == 'DELETE':
            return node.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ContributorOrPublicForPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (Node, Pointer)), 'obj must be a Node or Pointer, got {}'.format(obj)
        auth = get_user_auth(request)
        parent_node = Node.load(request.parser_context['kwargs']['node_id'])
        pointer_node = Pointer.load(request.parser_context['kwargs']['node_link_id']).node
        if request.method in permissions.SAFE_METHODS:
            has_parent_auth = parent_node.can_view(auth)
            has_pointer_auth = pointer_node.can_view(auth)
            public = obj.is_public
            has_auth = public or (has_parent_auth and has_pointer_auth)
            return has_auth
        else:
            has_auth = parent_node.can_edit(auth)
            return has_auth

class ContributorOrPublicForRelationshipPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        auth = get_user_auth(request)
        parent_node = obj['self']

        if request.method in permissions.SAFE_METHODS:
            return parent_node.can_view(auth)
        elif request.method == 'DELETE':
            return parent_node.can_edit(auth)
        else:
            has_parent_auth = parent_node.can_edit(auth)
            if not has_parent_auth:
                return False
            pointer_nodes = []
            for pointer in request.data.get('data', []):
                node = Node.load(pointer['id'])
                if not node or node.is_collection:
                    raise exceptions.NotFound(detail='Node with id "{}" was not found'.format(pointer['id']))
                pointer_nodes.append(node)
            has_pointer_auth = True
            for pointer in pointer_nodes:
                if not pointer.can_view(auth):
                    has_pointer_auth = False
                    break
            return has_pointer_auth


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Node):
            obj = Node.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        assert isinstance(obj, Node), 'obj must be a Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True
