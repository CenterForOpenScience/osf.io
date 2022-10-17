from rest_framework import generics, permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes
from api.base import permissions as base_permissions

from api.base.views import JSONAPIBaseView
from api.collection_submissions_actions.serializers import CollectionSubmissionActionSerializer
from api.base.parsers import (
    JSONSchemaParser,
    JSONAPIParser,
)
from api.subjects.views import SubjectRelationshipBaseView, BaseResourceSubjectsList
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.collections.permissions import (
    CanUpdateDeleteCGMOrPublic,
    CanSubmitToCollectionOrPublic,
    OnlyAdminOrModeratorCanDestroy
)
from api.collections.views import CollectionMixin

from osf.models import CollectionSubmission
from api.collection_submissions.serializers import CollectionSubmissionSerializer, CollectionSubmissionCreateSerializer
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error
from django.db.models import Q


class CollectionSubmissionDetail(JSONAPIBaseView, generics.RetrieveDestroyAPIView):
    permission_classes = (
        OnlyAdminOrModeratorCanDestroy,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION]

    serializer_class = CollectionSubmissionSerializer
    view_category = 'collection_submissions'
    view_name = 'collection-submissions-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        collected_resource_guid, collection_id = self.kwargs['collection_submission_id'].split('-')
        collection_submission = get_object_or_error(
            CollectionSubmission,
            Q(collection__guids___id=collection_id, guid___id=collected_resource_guid),
            self.request,
            'CollectionSubmission',
        )
        return collection_submission

    def perform_destroy(self, collection_submission):
        collection_submission.collection.remove_object(collection_submission)


class CollectionSubmissionList(JSONAPIBaseView, generics.ListCreateAPIView, CollectionMixin, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanSubmitToCollectionOrPublic,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION]

    model_class = CollectionSubmission
    serializer_class = CollectionSubmissionSerializer
    view_category = 'collection_submissions'
    view_name = 'collection-submission-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectionSubmissionCreateSerializer
        else:
            return CollectionSubmissionSerializer

    def get_default_queryset(self):
        return self.get_collection().collectionsubmission_set.all()

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        user = self.request.user
        collection = self.get_collection()
        serializer.save(creator=user, collection=collection)


class CollectionSubmissionDetailActionList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION_ACTION]

    parser_classes = (JSONAPIParser, JSONSchemaParser)

    serializer_class = CollectionSubmissionActionSerializer
    view_category = 'collection_submission_action'
    view_name = 'collection-submission-detail-action-list'


class CollectionSubmissionSubjectsList(BaseResourceSubjectsList, CollectionMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/collected_meta_subjects).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanUpdateDeleteCGMOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION_ACTION]

    view_category = 'collection_submissions'
    view_name = 'collection-submissions-subjects-list'

    def get_resource(self):
        return self.get_collection_submission()


class LegacyCollectionSubmissionDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, CollectionMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanUpdateDeleteCGMOrPublic,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION]

    serializer_class = CollectionSubmissionSerializer
    view_category = 'collection_submissions'
    view_name = 'legacy-collection-submissions-detail'

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_collection_submission()

    def perform_destroy(self, instance):
        # Skip collection permission check -- perms class checks when getting CGM
        collection = self.get_collection(check_object_permissions=False)
        collection.remove_object(instance)

    def perform_update(self, serializer):
        serializer.save()


class CollectionSubmissionSubjectsRelationshipList(SubjectRelationshipBaseView, CollectionMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/collected_meta_subjects_relationship).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanUpdateDeleteCGMOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.READ_COLLECTION_SUBMISSION]
    required_write_scopes = [CoreScopes.WRITE_COLLECTION_SUBMISSION]

    view_category = 'collection_submissions'
    view_name = 'collection-submissions-subjects-relationship-list'

    def get_resource(self, check_object_permissions=True):
        return self.get_collection_submission(check_object_permissions)
