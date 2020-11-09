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
    OSFGroup,
    OSFUser,
    Preprint,
    PrivateLink,
)
from osf.utils import permissions as osf_permissions

from api.base.utils import get_user_auth, is_deprecated, assert_resource_type


class ContributorOrPublic(permissions.BasePermission):

    acceptable_models = (AbstractNode, NodeRelation, Preprint, DraftRegistration)

    def has_object_permission(self, request, view, obj):
        from api.nodes.views import NodeStorageProvider
        if isinstance(obj, BaseAddonSettings):
            obj = obj.owner
        if isinstance(obj, NodeStorageProvider):
            obj = obj.node
        if isinstance(obj, dict):
            obj = obj.get('self', None)
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)

        if isinstance(obj, DraftRegistration) and isinstance(obj.branched_from, Node):
            obj = obj.branched_from

        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.can_edit(auth)


class IsPublic(permissions.BasePermission):

    acceptable_models = (AbstractNode,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        return obj.is_public or obj.can_view(auth)


class IsAdminContributor(permissions.BasePermission):
    """
    Use on API views where the requesting user needs to be an
    admin contributor to make changes.  Admin group membership
    is not sufficient.
    """
    acceptable_models = (AbstractNode, DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        # Old Registration workflow checks permissions on Node
        if isinstance(obj, DraftRegistration):
            obj = obj.branched_from
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.has_permission(auth.user, osf_permissions.ADMIN)
        else:
            return obj.is_admin_contributor(auth.user)


class EditIfPublic(permissions.BasePermission):

    acceptable_models = (AbstractNode,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        if request.method not in permissions.SAFE_METHODS:
            return obj.is_public
        return True


class IsAdmin(permissions.BasePermission):
    acceptable_models = (AbstractNode, PrivateLink,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        if isinstance(obj, PrivateLink):
            obj = view.get_node()
        auth = get_user_auth(request)
        return obj.has_permission(auth.user, osf_permissions.ADMIN)


class AdminDeletePermissions(permissions.BasePermission):
    acceptable_models = (AbstractNode, DraftRegistration)

    def has_object_permission(self, request, view, obj):
        """
        Admin perms are required to delete a node
        """
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method == 'DELETE':
            return obj.has_permission(auth.user, osf_permissions.ADMIN)
        return True


class IsContributorOrGroupMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, AbstractNode), 'obj must be an Node, got {}'.format(obj)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_contributor_or_group_member(auth.user)
        else:
            return obj.has_permission(auth.user, osf_permissions.WRITE)


class AdminOrPublic(permissions.BasePermission):

    acceptable_models = (AbstractNode, OSFUser, Institution, BaseAddonSettings, DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict) and 'self' in obj:
            obj = obj['self']

        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)

        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.has_permission(auth.user, osf_permissions.ADMIN)

class AdminContributorOrPublic(permissions.BasePermission):

    acceptable_models = (AbstractNode, DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        """
        To make changes, user must be an admin contributor. Admin group membership is not sufficient.
        """
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.can_view(auth)
        else:
            return obj.is_admin_contributor(auth.user)


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

class ReadOnlyIfWithdrawn(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Node):
            node = obj
        else:
            context = request.parser_context['kwargs']
            node = AbstractNode.load(context[view.node_lookup_url_kwarg])
        if node.is_retracted:
            return request.method in permissions.SAFE_METHODS
        return True

class ContributorDetailPermissions(permissions.BasePermission):
    """Permissions for contributor detail page."""

    acceptable_models = (AbstractNode, OSFUser, Contributor,)

    def load_resource(self, context, view):
        return AbstractNode.load(context[view.node_lookup_url_kwarg])

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        context = request.parser_context['kwargs']
        resource = self.load_resource(context, view)
        user = OSFUser.load(context['user_id'])
        if request.method in permissions.SAFE_METHODS:
            return resource.is_public or resource.can_view(auth)
        elif request.method == 'DELETE':
            return resource.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return resource.has_permission(auth.user, osf_permissions.ADMIN)


class NodeGroupDetailPermissions(permissions.BasePermission):
    """Permissions for node group detail - involving who can update the relationship
    between a node and an OSF Group."""

    acceptable_models = (OSFGroup, AbstractNode,)

    def load_resource(self, context, view):
        return AbstractNode.load(context[view.node_lookup_url_kwarg])

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        node = self.load_resource(request.parser_context['kwargs'], view)
        if request.method in permissions.SAFE_METHODS:
            return node.is_public or node.can_view(auth)
        elif request.method == 'DELETE':
            # If deleting an OSF group from a node, you either need admin perms
            # or you need to be an OSF group manager
            return node.has_permission(auth.user, osf_permissions.ADMIN) or obj.has_permission(auth.user, 'manage')
        else:
            return node.has_permission(auth.user, osf_permissions.ADMIN)


class ContributorOrPublicForPointers(permissions.BasePermission):

    acceptable_models = (AbstractNode, NodeRelation,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
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

    acceptable_models = (AbstractNode,)

    def has_object_permission(self, request, view, obj):
        # Preprints cannot be registrations
        if isinstance(obj, Preprint):
            return True

        if not isinstance(obj, AbstractNode):
            obj = AbstractNode.load(request.parser_context['kwargs'][view.node_lookup_url_kwarg])
        assert_resource_type(obj, self.acceptable_models)
        if obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True


class WriteAdmin(permissions.BasePermission):

    acceptable_models = (AbstractNode,)

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        return obj.can_edit(auth)


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
