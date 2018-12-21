# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import permissions
from rest_framework.exceptions import NotFound

from api.base.utils import get_user_auth
from osf.models import AbstractNode, Preprint, Collection, CollectionSubmission, CollectionProvider
from osf.utils.permissions import WRITE, ADMIN

class CollectionWriteOrPublic(permissions.BasePermission):
    # Adapted from ContributorOrPublic
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, CollectionSubmission):
            obj = obj.collection
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            if obj.is_public:
                return True
            return auth.user and auth.user.has_perm('read_collection', obj)
        return auth.user and auth.user.has_perm('write_collection', obj)

class ReadOnlyIfCollectedRegistration(permissions.BasePermission):
    """Makes PUT and POST forbidden for registrations."""
    # Adapted from ReadOnlyIfRegistration
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, AbstractNode) and obj.is_registration:
            return request.method in permissions.SAFE_METHODS
        return True

class CanSubmitToCollectionOrPublic(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (CollectionSubmission, Collection, CollectionProvider)), 'obj must be a Collection or CollectionSubmission, got {}'.format(obj)
        if isinstance(obj, CollectionSubmission):
            obj = obj.collection
        elif isinstance(obj, CollectionProvider):
            obj = obj.primary_collection
            if not obj:
                # Views either return empty QS or raise error in this case, let them handle it
                return True
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or auth.user and auth.user.has_perm('read_collection', obj)
        accepting_submissions = obj.is_public and obj.provider and obj.provider.allow_submissions
        return auth.user and (accepting_submissions or auth.user.has_perm('write_collection', obj))

class CanUpdateDeleteCGMOrPublic(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, CollectionSubmission), 'obj must be a CollectionSubmission, got {}'.format(obj)
        collection = obj.collection
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            return collection.is_public or auth.user and auth.user.has_perm('read_collection', collection)
        elif request.method in ['PUT', 'PATCH']:
            return obj.guid.referent.has_permission(auth.user, WRITE) or auth.user.has_perm('write_collection', collection)
        elif request.method == 'DELETE':
            # Restricted to collection and project admins.
            return obj.guid.referent.has_permission(auth.user, ADMIN) or auth.user.has_perm('admin_collection', collection)
        return False

class CollectionWriteOrPublicForPointers(permissions.BasePermission):
    # Adapted from ContributorOrPublicForPointers
    # Will only work for refs that point to AbstractNodes/Collections
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, (CollectionSubmission, Collection)), 'obj must be an Collection or CollectionSubmission, got {}'.format(obj)
        auth = get_user_auth(request)
        collection = Collection.load(request.parser_context['kwargs']['node_id'])
        pointer_node = collection.collectionsubmission_set.get(guid___id=request.parser_context['kwargs']['node_link_id']).guid.referent
        if request.method in permissions.SAFE_METHODS:
            has_collection_auth = auth.user and auth.user.has_perm('read_collection', collection)
            if isinstance(pointer_node, AbstractNode):
                has_pointer_auth = pointer_node.can_view(auth)
            elif isinstance(pointer_node, Collection):
                has_pointer_auth = auth.user and auth.user.has_perm('read_collection', pointer_node)
            public = pointer_node.is_public
            has_auth = public or (has_collection_auth and has_pointer_auth)
            return has_auth
        else:
            return auth.user and auth.user.has_perm('write_collection', collection)

class CollectionWriteOrPublicForRelationshipPointers(permissions.BasePermission):
    # Adapted from ContributorOrPublicForRelationshipPointers
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, dict)
        auth = get_user_auth(request)
        collection = obj['self']
        has_collection_auth = auth.user and auth.user.has_perm('write_collection', collection)

        if request.method in permissions.SAFE_METHODS:
            if collection.is_public:
                return True
        elif request.method == 'DELETE':
            return has_collection_auth

        if not has_collection_auth:
            return False
        pointer_objects = []
        for pointer in request.data.get('data', []):
            obj = AbstractNode.load(pointer['id']) or Preprint.load(pointer['id'])
            if not obj:
                raise NotFound(detail='Node with id "{}" was not found'.format(pointer['id']))
            pointer_objects.append(obj)
        has_pointer_auth = True
        # TODO: is this necessary? get_object checks can_view
        for pointer in pointer_objects:
            if not pointer.can_view(auth):
                has_pointer_auth = False
                break
        return has_pointer_auth
