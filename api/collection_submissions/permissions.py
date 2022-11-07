# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from api.base.utils import get_user_auth
from osf.models import CollectionSubmission
from osf.utils.permissions import READ
from api.base.utils import get_object_or_error
from django.db.models import Q
from rest_framework import exceptions, permissions


class CollectionContributorOrPublicOrModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        node_id, collection_id = view.kwargs['collection_submission_id'].split('-')
        if request.method == 'GET':
            obj = get_object_or_error(
                CollectionSubmission,
                Q(guid___id=node_id, collection__guids___id=collection_id),
                request,
                display_name='collection submission',
            )
            return self.has_object_permission(request, view, obj)
        else:
            raise exceptions.MethodNotAllowed(request.method)

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if obj.collection.is_public:
            return True
        else:
            return obj.guid.referent.has_permission(auth.user, READ) or auth.user in obj.collection.moderators
