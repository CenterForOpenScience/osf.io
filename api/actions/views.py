# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics
from rest_framework import permissions
from rest_framework.exceptions import NotFound, PermissionDenied

from api.actions.permissions import ReviewActionPermission
from api.actions.serializers import NodeRequestActionSerializer, ReviewActionSerializer, PreprintRequestActionSerializer
from api.base.exceptions import Conflict
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base import permissions as base_permissions
from api.base.utils import absolute_reverse
from api.requests.views import NodeRequestMixin, PreprintRequestMixin
from api.requests.permissions import NodeRequestPermission, PreprintRequestPermission
from framework.auth.oauth_scopes import CoreScopes
from osf.models import PreprintProvider, ReviewAction, NodeRequestAction, PreprintRequestAction


def get_review_actions_queryset():
    return ReviewAction.objects.include(
        'creator__guids',
        'target__guids',
        'target__provider',
    ).filter(is_deleted=False)


class ActionDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Action Detail

    Actions represent state changes and/or comments on any actionable object (e.g. preprints, noderequests)

    ##Action Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the action was created
        date_modified                   iso8601 timestamp                   timestamp that the action was last modified
        from_state                      string                              state of the reviewable before this action was created
        to_state                        string                              state of the reviewable after this action was created
        comment                         string                              comment explaining the state change
        trigger                         string                              name of the trigger for this action

    ##Relationships

    ###Target
    Link to the object (e.g. preprint) this action acts on

    ###Provider
    Link to detail for the target object's provider

    ###Creator
    Link to the user that created this action

    ##Links
    - `self` -- Detail page for the current action
    """
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReviewActionPermission,
        # TODO: Consider generic "ActionPermission" when RequestActions are viewable
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    serializer_class = ReviewActionSerializer
    view_category = 'actions'
    view_name = 'action-detail'

    def get_serializer_class(self):
        # Not allowed to view NodeRequestActions yet, making extra logic unnecessary
        return ReviewActionSerializer

    def get_object(self):
        action = None
        if ReviewAction.objects.filter(_id=self.kwargs['action_id']).exists():
            action = get_object_or_404(get_review_actions_queryset(), _id=self.kwargs['action_id'])
        elif NodeRequestAction.objects.filter(_id=self.kwargs['action_id']).exists() or PreprintRequestAction.objects.filter(_id=self.kwargs['action_id']).exists():
            # No permissions allow for viewing RequestActions yet
            raise PermissionDenied('You do not have permission to view this Action')
        if not action:
            raise NotFound('Unable to find specified Action')
        self.check_object_permissions(self.request, action)
        return action


class ReviewActionListCreate(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    """List of review actions viewable by this user

    Actions represent state changes and/or comments on a reviewable object (e.g. a preprint)

    ##Action Attributes

        name                            type                                description
        ====================================================================================
        date_created                    iso8601 timestamp                   timestamp that the action was created
        date_modified                   iso8601 timestamp                   timestamp that the action was last modified
        from_state                      string                              state of the reviewable before this action was created
        to_state                        string                              state of the reviewable after this action was created
        comment                         string                              comment explaining the state change
        trigger                         string                              name of the trigger for this action

    ##Relationships

    ###Target
    Link to the object (e.g. preprint) this action acts on

    ###Provider
    Link to detail for the target object's provider

    ###Creator
    Link to the user that created this action

    ##Links
    - `self` -- Detail page for the current action

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Actions may be filtered by their `id`, `from_state`, `to_state`, `date_created`, `date_modified`, `creator`, `provider`, `target`
    """
    # Permissions handled in get_default_django_query
    permission_classes = (
        permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        ReviewActionPermission,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = ReviewActionSerializer
    model_class = ReviewAction

    ordering = ('-created',)
    view_category = 'actions'
    view_name = 'review-action-list'

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        if not target.provider.is_reviewed:
            raise Conflict('{} is an unmoderated provider. If you are an admin, set up moderation by setting `reviews_workflow` at {}'.format(
                target.provider.name,
                absolute_reverse(
                    'providers:preprint-providers:preprint-provider-detail', kwargs={
                        'provider_id': target.provider._id,
                        'version': self.request.parser_context['kwargs']['version'],
                    },
                ),
            ))

        serializer.save(user=self.request.user)

    # overrides ListFilterMixin
    def get_default_queryset(self):
        provider_queryset = get_objects_for_user(self.request.user, 'view_actions', PreprintProvider)
        return get_review_actions_queryset().filter(target__node__is_public=True, target__provider__in=provider_queryset)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

class NodeRequestActionCreate(JSONAPIBaseView, generics.CreateAPIView, NodeRequestMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        NodeRequestPermission,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = NodeRequestActionSerializer

    view_category = 'request-actions'
    view_name = 'create-node-request-action'

    # overrides CreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        serializer.save(user=self.request.user)

class PreprintRequestActionCreate(JSONAPIBaseView, generics.CreateAPIView, PreprintRequestMixin):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintRequestPermission,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = PreprintRequestActionSerializer

    view_category = 'request-actions'
    view_name = 'create-preprint-request-action'

    # overrides CreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        serializer.save(user=self.request.user)
