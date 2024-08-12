from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.views import JSONAPIBaseView
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.collection_submission_actions.serializers import (
    CollectionSubmissionActionSerializer,
)
from api.collections.permissions import (
    CollectionReadOrPublic,
    CollectionSubmissionActionListPermission,
)
from api.collection_submission_actions.schemas import (
    create_collection_action_payload,
)

from osf.models import CollectionSubmissionAction


class CollectionSubmissionActionDetail(
    JSONAPIBaseView,
    generics.RetrieveAPIView,
):
    permission_classes = (
        CollectionReadOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION_ACTION]

    serializer_class = CollectionSubmissionActionSerializer
    view_category = "collection_submission_actions"
    view_name = "collection-submission-action-detail"

    def get_object(self):
        return get_object_or_error(
            CollectionSubmissionAction,
            self.kwargs["action_id"],
            self.request,
            display_name="CollectionSubmissionAction",
        )


class CollectionSubmissionActionList(JSONAPIBaseView, generics.CreateAPIView):
    permission_classes = (
        CollectionSubmissionActionListPermission,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION_ACTION]

    parser_classes = (
        JSONAPIMultipleRelationshipsParser,
        JSONAPIMultipleRelationshipsParserForRegularJSON,
    )

    serializer_class = CollectionSubmissionActionSerializer
    view_category = "collection_submission_actions"
    view_name = "collection-submission-action-list"

    create_payload_schema = create_collection_action_payload

    def get_parser_context(self, http_request):
        """
        Tells parser what json schema we are checking against.
        """
        res = super().get_parser_context(http_request)
        res["json_schema"] = self.create_payload_schema
        return res
