# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from api.base.exceptions import Conflict
from api.base.filters import ListFilterMixin
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import absolute_reverse
from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.preprints.views import PreprintMixin
from framework.auth.oauth_scopes import CoreScopes
from osf.models import PreprintProvider
from reviews import permissions as reviews_permissions
from reviews.models import ReviewLog
from reviews.serializers import ReviewLogSerializer


class ReviewLogMixin:
    def review_logs_queryset(self):
        return ReviewLog.objects.include(
            'creator',
            'creator__guids',
            'reviewable',
            'reviewable__guids',
            'reviewable__provider',
        ).filter(is_deleted=False)


class LogDetail(JSONAPIBaseView, generics.RetrieveAPIView, ReviewLogMixin):
    """Review Log Detail

    Review logs represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Review Log Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the review log was created
        date_modified                   iso8601 timestamp                   timestamp that the review log was last modified
        from_state                      string                              state of the reviewable before this log was created
        to_state                        string                              state of the reviewable after this log was created
        comment                         string                              comment explaining the state change

    ##Relationships

    ###Reviewable
    Link to the reviewable object (e.g. preprint) this review log refers to

    ###Provider
    Link to detail for the reviewable's provider

    ###Creator
    Link to the user that created this log

    ##Links
    - `self` -- Detail page for the current review log
    """
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        reviews_permissions.LogPermission,
    )

    required_read_scopes = [CoreScopes.REVIEW_LOGS_READ]
    required_write_scopes = [CoreScopes.REVIEW_LOGS_WRITE]

    serializer_class = ReviewLogSerializer
    view_category = 'reviews'
    view_name = 'review_log-detail'

    def get_object(self):
        log = get_object_or_404(self.review_logs_queryset(), _id=self.kwargs['log_id'])
        self.check_object_permissions(self.request, log)
        return log


class LogList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, ReviewLogMixin):
    """Review Log List *Writable*

    Review logs represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Review Log Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the review log was created
        date_modified                   iso8601 timestamp                   timestamp that the review log was last modified
        from_state                      string                              state of the reviewable before this log was created
        to_state                        string                              state of the reviewable after this log was created
        comment                         string                              comment explaining the state change

    ##Relationships

    ###Reviewable
    Link to the reviewable object (e.g. preprint) this review log refers to

    ###Provider
    Link to detail for the reviewable's provider

    ###Creator
    Link to the user that created this log

    ##Links
    - `self` -- Detail page for the current review log

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Review logs may be filtered by their `id`, `from_state`, `to_state`, `date_created`, `date_modified`, `creator`, `provider`, `reviewable`
    Most are string fields and will be filtered using simple substring matching.
    """
    # Permissions handled in get_default_django_query
    permission_classes = (
        permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        reviews_permissions.LogPermission,
    )

    required_read_scopes = [CoreScopes.REVIEW_LOGS_READ]
    required_write_scopes = [CoreScopes.REVIEW_LOGS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = ReviewLogSerializer

    ordering = ('-date_created',)
    view_category = 'reviews'
    view_name = 'review_log-list'

    # overrides ListFilterMixin
    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        provider_queryset = get_objects_for_user(auth.user, 'view_review_logs', PreprintProvider)
        return self.review_logs_queryset().filter(reviewable__provider__in=provider_queryset)

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        reviewable = serializer.validated_data['reviewable']
        self.check_object_permissions(self.request, reviewable)

        action = serializer.validated_data['action']
        permission = reviews_permissions.ACTION_PERMISSIONS[action]
        if permission is not None and not self.request.user.has_perm(permission, reviewable.provider):
            raise PermissionDenied(detail='Performing action "{}" requires permission "{}" on the provider.'.format(action, permission))

        if not reviewable.provider.is_moderated:
            raise Conflict('{} is an unmoderated provider. If you are an admin, set up moderation by setting `reviews_workflow` at {}'.format(
                reviewable.provider.name,
                absolute_reverse('preprint_providers:preprint_provider-detail', kwargs={
                    'provider_id': reviewable.provider._id,
                    'version': self.request.parser_context['kwargs']['version']
                })
            ))

        serializer.save(user=self.request.user)

    # overrides ListCreateAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class PreprintReviewLogList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, PreprintMixin, ReviewLogMixin):
    """Review Log List *Read-only*

    Review logs represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Review Log Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the review log was created
        date_modified                   iso8601 timestamp                   timestamp that the review log was last modified
        from_state                      string                              state of the reviewable before this log was created
        to_state                        string                              state of the reviewable after this log was created
        comment                         string                              comment explaining the state change

    ##Relationships

    ###Reviewable
    Link to the reviewable object (e.g. preprint) this review log refers to

    ###Provider
    Link to detail for the reviewable's provider

    ###Creator
    Link to the user that created this log

    ##Links
    - `self` -- Detail page for the current review log

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Review logs may be filtered by their `id`, `from_state`, `to_state`, `date_created`, `date_modified`, `provider`, `reviewable`
    Most are string fields and will be filtered using simple substring matching.
    """
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        reviews_permissions.LogPermission,
    )

    required_read_scopes = [CoreScopes.REVIEW_LOGS_READ]
    required_write_scopes = [CoreScopes.REVIEW_LOGS_WRITE]

    serializer_class = ReviewLogSerializer

    ordering = ('-date_created',)
    view_category = 'reviews'
    view_name = 'reviewable-review_log-list'

    # overrides ListFilterMixin
    def get_default_queryset(self):
        return self.review_logs_queryset().filter(reviewable_id=self.get_preprint().id)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
