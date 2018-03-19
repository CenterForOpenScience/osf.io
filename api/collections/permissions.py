# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import permissions
from rest_framework.exceptions import NotFound

from api.base.utils import get_user_auth
from osf.models import AbstractNode, Collection, CollectedGuidMetadata

class CreatorOrAdminOrPublic(permissions.BasePermission):
    # Adapted from ContributorOrPublic
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, CollectedGuidMetadata):
            obj = obj.collection
        if request.method in permissions.SAFE_METHODS:
            if obj.is_public:
                return True
        auth = get_user_auth(request)
        # TODO [IN-152]: Use django-guardian. For now, only creators
        return obj.creator == auth.user

class ReadOnlyIfCollectedRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""
    # Adapted from ReadOnlyIfRegistration
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, AbstractNode) and obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True

class CreatorOrAdminOrPublicForPointers(permissions.BasePermission):
    # Adapted from ContributorOrPublicForPointers
    # Will only work for refs that point to AbstractNodes/Collections
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (CollectedGuidMetadata, Collection)), 'obj must be an Collection or CollectedGuidMetadata, got {}'.format(obj)
        auth = get_user_auth(request)
        collection = Collection.load(request.parser_context['kwargs']['node_id'])
        pointer_node = collection.collectedguidmetadata_set.get(guid___id=request.parser_context['kwargs']['node_link_id']).guid.referent
        if request.method in permissions.SAFE_METHODS:
            has_collection_auth = collection.creator == auth.user
            if isinstance(pointer_node, AbstractNode):
                has_pointer_auth = pointer_node.can_view(auth)
            elif isinstance(pointer_node, Collection):
                has_pointer_auth = pointer_node.creator == auth.user
            public = pointer_node.is_public
            has_auth = public or (has_collection_auth and has_pointer_auth)
            return has_auth
        else:
            return collection.creator == auth.user

class CreatorOrAdminOrPublicForRelationshipPointers(permissions.BasePermission):
    # Adapted from ContributorOrPublicForRelationshipPointers
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        auth = get_user_auth(request)
        collection = obj['self']
        has_collection_auth = collection.creator == auth.user

        if request.method in permissions.SAFE_METHODS:
            if collection.is_public:
                return True
        elif request.method == 'DELETE':
            return has_collection_auth

        if not has_collection_auth:
            return False
        pointer_nodes = []
        for pointer in request.data.get('data', []):
            node = AbstractNode.load(pointer['id'])
            if not node:
                raise NotFound(detail='Node with id "{}" was not found'.format(pointer['id']))
            pointer_nodes.append(node)
        has_pointer_auth = True
        # TODO: is this necessary? get_object checks can_view
        for pointer in pointer_nodes:
            if not pointer.can_view(auth):
                has_pointer_auth = False
                break
        return has_pointer_auth
