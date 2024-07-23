from api.base.utils import get_user_auth
from osf.models import CollectionSubmission
from osf.utils.permissions import READ
from api.base.utils import get_object_or_error
from rest_framework import exceptions, permissions


class CollectionSubmissionActionsListPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != 'GET':
            raise exceptions.MethodNotAllowed(request.method)

        node_id, collection_id = view.kwargs['collection_submission_id'].split('-')
        obj = get_object_or_error(
            CollectionSubmission.objects.filter(
                guid___id=node_id,
                collection__guids___id=collection_id,
            ),
            request=request,
            display_name='collection submission',
        )
        return self.has_object_permission(request, view, obj)

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if obj.collection.is_public:
            return True
        else:
            is_moderator = auth.user and auth.user.has_perm('view_submissions', obj.collection.provider)
            return obj.guid.referent.has_permission(auth.user, READ) or is_moderator
