from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.collection_submissions_actions.serializers import CollectionSubmissionActionSerializer

from osf.models import CollectionSubmissionAction
from api.collections.permissions import CollectionReadOrPublic


class CollectionSubmissionActionDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        CollectionReadOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION_ACTION]

    serializer_class = CollectionSubmissionActionSerializer
    view_category = 'collection_submissions_actions'
    view_name = 'collection-submission-action-detail'

    def get_object(self):
        return get_object_or_error(
            CollectionSubmissionAction,
            self.kwargs['action_id'],
            self.request,
            display_name='CollectionSubmissionAction',
        )
