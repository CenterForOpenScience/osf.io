from rest_framework import generics, permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes
from api.base import permissions as base_permissions
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON

from api.base.views import JSONAPIBaseView
from api.collections.permissions import (
    CanUpdateDeleteCollectionSubmissionOrPublic,
)
from api.collections.serializers import (
    CollectionSubmissionSerializer,
)

from api.collections.views import CollectionMixin


class CollectionSubmissionDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, CollectionMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanUpdateDeleteCollectionSubmissionOrPublic,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.COLLECTED_META_READ]
    required_write_scopes = [CoreScopes.COLLECTED_META_WRITE]

    serializer_class = CollectionSubmissionSerializer
    view_category = 'collections'
    view_name = 'collected-metadata-detail'

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_collection_submission()

    def perform_destroy(self, instance):
        # Skip collection permission check -- perms class checks when getting CollectionSubmission
        collection = self.get_collection(check_object_permissions=False)
        collection.remove_object(instance)

    def perform_update(self, serializer):
        serializer.save()
