from __future__ import unicode_literals

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from api.base.filters import ListFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.versioning import PrivateVersioning
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.chronos.permissions import SubmissionOnPreprintPublishedOrAdmin
from api.chronos.serializers import ChronosJournalSerializer, ChronosSubmissionSerializer, ChronosSubmissionCreateSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import ChronosJournal, ChronosSubmission, PreprintService


class ChronosJournalList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = ChronosJournalSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'chronos'
    view_name = 'chronos-journals'

    def get_default_queryset(self):
        return ChronosJournal.objects.all()

    def get_queryset(self):
        return self.get_queryset_from_request()


class ChronosJournalDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = ChronosJournalSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'chronos'
    view_name = 'chronos-journal-detail'

    def get_object(self):
        try:
            return ChronosJournal.objects.get(journal_id=self.kwargs['journal_id'])
        except ChronosJournal.DoesNotExist:
            raise NotFound


class ChronosSubmissionList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        SubmissionOnPreprintPublishedOrAdmin,
    )
    required_read_scopes = [CoreScopes.CHRONOS_SUBMISSION_READ]
    required_write_scopes = [CoreScopes.CHRONOS_SUBMISSION_WRITE]

    serializer_class = ChronosSubmissionSerializer
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'chronos'
    view_name = 'chronos-submissions'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChronosSubmissionCreateSerializer
        else:
            return ChronosSubmissionSerializer

    def get_default_queryset(self):
        return ChronosSubmission.objects.filter(
            preprint__guids___id=self.kwargs['preprint_id']
        )

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        user = self.request.user
        preprint = PreprintService.load(self.kwargs['preprint_id'])
        if not preprint:
            raise NotFound
        self.check_object_permissions(self.request, preprint)
        serializer.save(submitter=user, preprint=preprint)


class ChronosSubmissionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        SubmissionOnPreprintPublishedOrAdmin,
    )
    required_read_scopes = [CoreScopes.CHRONOS_SUBMISSION_READ]
    required_write_scopes = [CoreScopes.CHRONOS_SUBMISSION_WRITE]

    serializer_class = ChronosSubmissionSerializer

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning
    view_category = 'chronos'
    view_name = 'chronos-submission-detail'

    def get_object(self):
        try:
            submission = ChronosSubmission.objects.get(publication_id=self.kwargs['submission_id'])
        except ChronosSubmission.DoesNotExist:
            raise NotFound
        else:
            self.check_object_permissions(self.request, submission)
            return submission
