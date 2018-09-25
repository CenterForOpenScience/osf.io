# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from api.base.utils import get_user_auth
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


class SubmissionAcceptedOrPublishedOrPreprintContributor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChronosSubmission):
            submission = ChronosSubmission.objects.get(publication_id=view.kwargs.get('submission_id', None))
            node = obj.preprint.node
            auth = get_user_auth(request)

            is_preprint_contributor = node.is_contributor(auth.user)
            is_submission_accepted = submission.status == 3
            is_submission_published = submission.status == 4
            user_has_perm = is_preprint_contributor or is_submission_published or is_submission_accepted

            # If the user has no permission to view this submission
            # raise NotFound instead of PermissionDenied
            # so that malicious users can't sniff out whether a preprint has Chronos submission or not
            if not user_has_perm:
                raise exceptions.NotFound
            else:
                return user_has_perm
