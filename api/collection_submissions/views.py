from rest_framework import generics, permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error

from api.collection_submissions.permissions import (
    CollectionSubmissionActionsListPermission,
)
from api.collection_submission_actions.serializers import (
    CollectionSubmissionActionSerializer,
)

from osf.models import CollectionSubmission


class CollectionSubmissionActionsList(
    JSONAPIBaseView, generics.ListAPIView, ListFilterMixin
):
    permission_classes = (
        CollectionSubmissionActionsListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION_ACTION]

    view_category = "collections"
    view_name = "collection-submission-action-list"

    def get_serializer_class(self):
        return CollectionSubmissionActionSerializer

    def get_default_queryset(self):
        node_id, collection_id = self.kwargs["collection_submission_id"].split(
            "-"
        )

        return get_object_or_error(
            CollectionSubmission.objects.filter(
                guid___id=node_id,
                collection__guids___id=collection_id,
            ),
            request=self.request,
            display_name="collection submission",
        ).actions.all()

    def get_queryset(self):
        return self.get_queryset_from_request()
