import io

from rest_framework import permissions
from rest_framework.exceptions import NotFound, MethodNotAllowed

from api.base.exceptions import Gone
from api.base.parsers import JSONSchemaParser
from api.base.utils import get_user_auth, assert_resource_type, get_object_or_error
from osf.models import AbstractNode, Preprint, Collection, CollectionSubmission, CollectionProvider
from osf.utils.permissions import WRITE, ADMIN


class CollectionReadOrPublic(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return self.has_object_permission(request, view, view.get_object())
        else:
            raise MethodNotAllowed(request.method)

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user and auth.user.has_perm('view_submissions', obj.target.collection.provider):
            return True
        elif obj.target.guid.referent.can_view(auth):
            return True
        else:
            return False


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
        assert isinstance(obj, (CollectionSubmission, Collection, CollectionProvider)), f'obj must be a Collection or CollectionSubmission, got {obj}'
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

class CanUpdateDeleteCollectionSubmissionOrPublic(permissions.BasePermission):

    acceptable_models = (CollectionSubmission,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            obj = obj.get('self', None)

        assert_resource_type(obj, self.acceptable_models)
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
        assert isinstance(obj, (CollectionSubmission, Collection)), f'obj must be an Collection or CollectionSubmission, got {obj}'
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


class CollectionSubmissionActionListPermission(permissions.BasePermission):

    acceptable_models = (CollectionSubmission,)

    def has_object_permission(self, request, view, collection_submission):
        if request.method != 'POST':
            raise MethodNotAllowed(request.method)

        assert_resource_type(collection_submission, self.acceptable_models)
        auth = get_user_auth(request)
        provider = collection_submission.collection.provider
        is_moderator = bool(auth.user and auth.user.has_perm('accept_submissions', provider))
        return collection_submission.guid.referent.has_permission(auth.user, ADMIN) or is_moderator

    def has_permission(self, request, view):
        if request.method != 'POST':
            raise MethodNotAllowed(request.method)

        # Validate json before using id to check for permissions
        request_json = JSONSchemaParser().parse(
            io.BytesIO(request.body),
            parser_context={
                'request': request,
                'json_schema': view.create_payload_schema,
            },
        )
        try:
            hyphen_id = request_json['data']['relationships']['target']['data']['id']
            node_guid, collection_guid = hyphen_id.split('-')
        except ValueError:
            raise NotFound(f'Your id [`{hyphen_id}`] was not valid.')

        obj = get_object_or_error(
            CollectionSubmission.objects.filter(
                guid___id=node_guid,
                collection__guids___id=collection_guid,
            ),
            request=request,
            display_name='collection submission',
        )
        if obj.guid.referent.deleted:
            raise Gone()

        return self.has_object_permission(request, view, obj)
