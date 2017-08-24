# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics

from api.base.views import JSONAPIBaseView
from api.base.filters import DjangoFilterMixin
from api.preprints.views import PreprintMixin
from reviews.models import ReviewLog
from reviews.serializers import ReviewLogSerializer


class LogDetail(JSONAPIBaseView, generics.RetrieveAPIView):
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

    # TODO permissions (MOD-22)

    serializer_class = ReviewLogSerializer
    view_category = 'reviews'
    view_name = 'review_log-detail'

    def get_object(self):
        return get_object_or_404(ReviewLog, _id=self.kwargs['log_id'])


class LogList(JSONAPIBaseView, generics.ListAPIView, DjangoFilterMixin):
    """Review Log List

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
    # TODO permissions (MOD-22)

    serializer_class = ReviewLogSerializer

    ordering = ('-date_created',)
    view_category = 'reviews'
    view_name = 'review_log-list'

    # overrides DjangoFilterMixin
    def get_default_django_query(self):
        return Q()

    # overrides ListAPIView
    def get_queryset(self):
        return ReviewLog.objects.select_related('reviewable', 'reviewable__provider').filter(self.get_query_from_request()).distinct()


class ReviewableLogList(JSONAPIBaseView, generics.ListAPIView, DjangoFilterMixin, PreprintMixin):
    """Review Log List

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
    # TODO permissions (MOD-22)
    # TODO allow creating log for this reviewable (MOD-48)

    serializer_class = ReviewLogSerializer

    ordering = ('-date_created',)
    view_category = 'reviews'
    view_name = 'reviewable-review_log-list'

    # overrides DjangoFilterMixin
    def get_default_django_query(self):
        return Q(reviewable_id=self.get_preprint().id)

    # overrides ListAPIView
    def get_queryset(self):
        return ReviewLog.objects.select_related('reviewable', 'reviewable__provider').filter(self.get_query_from_request()).distinct()
