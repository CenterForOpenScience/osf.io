# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from addons.base.models import BaseAddonSettings
from osf.models import (
    AbstractNode,
    Contributor,
    DraftRegistration,
    Institution,
    Node,
    NodeRelation,
    OSFUser,
    PreprintService,
    PrivateLink,
)
from osf.utils import permissions as osf_permissions
from website.project.metadata.utils import is_prereg_admin

from api.base.utils import get_user_auth, is_deprecated


class ContributorOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        from api.nodes.views import NodeProvider
        if isinstance(obj, BaseAddonSettings):
            obj = obj.owner
        if isinstance(obj, (NodeProvider, PreprintService)):
            obj = obj.node
        assert isinstance(obj, (AbstractNode, NodeRelation)), 'obj must be an Node, NodeProvider, NodeRelation, PreprintService, or AddonSettings; got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)


class IsPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, AbstractNode), 'obj must be an Node got {}'.format(obj)
        auth = get_user_auth(request)
        return obj.is_public or obj.can_view(auth)


class IsAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, AbstractNode), 'obj must be an Node, got {}'.format(obj)
        auth = get_user_auth(request)
        return obj.has_permission(auth.user, osf_permissions.ADMIN)


class IsAdminOrReviewer(permissions.BasePermission):
    """
    Prereg admins can update draft registrations.
    """
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (AbstractNode, DraftRegistration, PrivateLink)), 'obj must be an Node, Draft Registration, or PrivateLink, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method != 'DELETE' and is_prereg_admin(auth.user):
            return True
        return obj.has_permission(auth.user, osf_permissions.ADMIN)


class AdminOrPublic(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (AbstractNode, OSFUser, Institution, BaseAddonSettings, DraftRegistration, PrivateLink)), 'obj must be an Node, User, Institution, Draft Registration, PrivateLink, or AddonSettings; got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.has_permission(auth.user, osf_permissions.ADMIN)


class ExcludeWithdrawals(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Node):
            node = obj
        else:
            context = request.parser_context['kwargs']
            node = AbstractNode.load(context[view.node_lookup_url_kwarg])
        if node.is_retracted:
            return False
        return True


class ContributorDetailPermissions(permissions.BasePermission):
    """Permissions for contributor detail page."""

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (AbstractNode, OSFUser, Contributor)), 'obj must be User, Contributor, or Node, got {}'.format(obj)
        auth = get_user_auth(request)
        context = request.parser_context['kwargs']
        node = AbstractNode.load(context[view.node_lookup_url_kwarg])
        user = OSFUser.load(context['user_id'])
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        elif request.method == 'DELETE':
            return node.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ContributorOrPublicForPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (AbstractNode, NodeRelation)), 'obj must be an Node or NodeRelation, got {}'.format(obj)
        auth = get_user_auth(request)
        parent_node = AbstractNode.load(request.parser_context['kwargs']['node_id'])
        pointer_node = NodeRelation.load(request.parser_context['kwargs']['node_link_id']).child
        if request.method in permissions.SAFE_METHODS:
            has_parent_auth = parent_node.can_view(auth)
            has_pointer_auth = pointer_node.can_view(auth)
            public = pointer_node.is_public
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
                node = AbstractNode.load(pointer['id'])
                if not node or node.is_collection:
                    raise exceptions.NotFound(detail='Node with id "{}" was not found'.format(pointer['id']))
                pointer_nodes.append(node)
            has_pointer_auth = True
            for pointer in pointer_nodes:
                if not pointer.can_view(auth):
                    has_pointer_auth = False
                    break
            return has_pointer_auth


class RegistrationAndPermissionCheckForPointers(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        node_link = NodeRelation.load(request.parser_context['kwargs']['node_link_id'])
        node = AbstractNode.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        auth = get_user_auth(request)
        if request.method == 'DELETE'and node.is_registration:
            raise exceptions.MethodNotAllowed(method=request.method)
        if node.is_collection or node.is_registration:
            raise exceptions.NotFound
        if node != node_link.parent:
            raise exceptions.NotFound
        if request.method == 'DELETE' and not node.can_edit(auth):
            return False
        return True


class WriteOrPublicForRelationshipInstitutions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        auth = get_user_auth(request)
        node = obj['self']

        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        else:
            return node.has_permission(auth.user, osf_permissions.WRITE)


class ReadOnlyIfRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, AbstractNode):
            obj = AbstractNode.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        assert isinstance(obj, AbstractNode), 'obj must be an Node'
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True


class ShowIfVersion(permissions.BasePermission):

    def __init__(self, min_version, max_version, deprecated_message):
        super(ShowIfVersion, self).__init__()
        self.min_version = min_version
        self.max_version = max_version
        self.deprecated_message = deprecated_message

    def has_object_permission(self, request, view, obj):
        if is_deprecated(request.version, self.min_version, self.max_version):
            raise exceptions.NotFound(detail=self.deprecated_message)
        return True


class NodeLinksShowIfVersion(ShowIfVersion):

    def __init__(self):
        min_version = '2.0'
        max_version = '2.0'
        deprecated_message = 'This feature is deprecated as of version 2.1'
        super(NodeLinksShowIfVersion, self).__init__(min_version, max_version, deprecated_message)
