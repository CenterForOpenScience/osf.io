# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from api.preprints.permissions import PreprintPublishedOrAdmin
from osf.models import ChronosSubmission, PreprintService

class SubmissionOnPreprintPublishedOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        preprint = PreprintService.load(view.kwargs.get('preprint_id', None))
        if not preprint:
            raise exceptions.NotFound
        return PreprintPublishedOrAdmin().has_object_permission(request, view, preprint)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChronosSubmission):
            obj = obj.preprint
        return PreprintPublishedOrAdmin().has_object_permission(request, view, obj)
