# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import permissions

from framework.auth.oauth_scopes import CoreScopes
from osf.models import Action
from reviews import permissions as reviews_permissions

from api.actions.serializers import ActionSerializer
from api.base.exceptions import Conflict
from api.base.parsers import (
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.utils import absolute_reverse
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions


def get_actions_queryset():
    return Action.objects.include(
        'creator',
        'creator__guids',
        'target',
        'target__guids',
        'target__provider',
    ).filter(is_deleted=False)


class ActionDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Action Detail

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
    """
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        reviews_permissions.ActionPermission,
    )

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    serializer_class = ActionSerializer
    view_category = 'actions'
    view_name = 'action-detail'

    def get_object(self):
        action = get_object_or_404(get_actions_queryset(), _id=self.kwargs['action_id'])
        self.check_object_permissions(self.request, action)
        return action


class CreateAction(JSONAPIBaseView, generics.ListCreateAPIView):
    """Create Actions *Write-only*

    Use this endpoint to create a new Action and thereby trigger a state change on a preprint.

    GETting from this endpoint will always return an empty list.
    Use `/user/me/actions/` or `/preprints/<guid>/actions/` to read lists of actions.

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

    ###Creating New Actions

    Create a new Action by POSTing to `/actions/`, including the target preprint and the action trigger.

    Valid triggers are: `submit`, `accept`, `reject`, and `edit_comment`

        Method:        POST
        URL:           /actions/
        Query Params:  <none>
        Body (JSON):   {
                        "data": {
                            "attributes": {
                                "trigger": {trigger},           # required
                                "comment": {comment},
                            },
                            "relationships": {
                                "target": {                     # required
                                    "data": {
                                        "type": "preprints",
                                        "id": {preprint_id}
                                    }
                                },
                            }
                        }
                    }
        Success:       201 CREATED + action representation
    """
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        reviews_permissions.ActionPermission,
    )

    required_read_scopes = [CoreScopes.NULL]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = ActionSerializer

    view_category = 'actions'
    view_name = 'create-action'

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        target = serializer.validated_data['target']
        self.check_object_permissions(self.request, target)

        if not target.provider.is_reviewed:
            raise Conflict('{} is an unmoderated provider. If you are an admin, set up moderation by setting `reviews_workflow` at {}'.format(
                target.provider.name,
                absolute_reverse('preprint_providers:preprint_provider-detail', kwargs={
                    'provider_id': target.provider._id,
                    'version': self.request.parser_context['kwargs']['version']
                })
            ))

        serializer.save(user=self.request.user)

    # overrides ListCreateAPIView
    def get_queryset(self):
        return Action.objects.none()
