# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from api.base.utils import get_user_auth
from api.preprints.permissions import PreprintPublishedOrAdmin
from osf.models import ChronosSubmission, Preprint
from osf.utils import permissions as osf_permissions


class SubmissionOnPreprintPublishedOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        preprint = Preprint.load(view.kwargs.get('preprint_id', None))
        if not preprint:
            raise exceptions.NotFound
        return PreprintPublishedOrAdmin().has_object_permission(request, view, preprint)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChronosSubmission):
            obj = obj.preprint
        return PreprintPublishedOrAdmin().has_object_permission(request, view, obj)


class SubmissionAcceptedOrPublishedOrPreprintAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChronosSubmission):
            submission = ChronosSubmission.objects.get(publication_id=view.kwargs.get('submission_id', None))
            auth = get_user_auth(request)

            is_submission_accepted = submission.status == 3
            is_submission_published = submission.status == 4

            user_has_perm = False
            # If the request is a GET, then check whether the user is a CONTRIBUTOR
            # Because it is okay for us to show contributors detail of all submissions of this preprint
            if request.method == 'GET':
                is_preprint_contributor = obj.preprint.is_contributor(auth.user)
                user_has_perm = is_preprint_contributor or is_submission_published or is_submission_accepted
                if not user_has_perm:
                    raise exceptions.NotFound

            # However if the request is a PATCH or PUT, check whether the user is an ADMIN of this preprint
            # Because only preprint admins can update a submission
            if request.method in ['PATCH', 'PUT']:
                is_preprint_admin = obj.preprint.has_permission(auth.user, osf_permissions.ADMIN)
                user_has_perm = is_preprint_admin
                if not user_has_perm:
                    raise exceptions.PermissionDenied

            return user_has_perm
