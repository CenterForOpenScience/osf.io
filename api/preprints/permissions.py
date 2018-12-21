# -*- coding: utf-8 -*-
from rest_framework import permissions
from rest_framework import exceptions

from api.base.utils import get_user_auth, assert_resource_type
from api.nodes.permissions import (
    AdminOrPublic as NodeAdminOrPublic,
)
from osf.models import Preprint, OSFUser, PreprintContributor, Identifier
from addons.osfstorage.models import OsfStorageFolder
from osf.utils.workflows import DefaultStates
from osf.utils import permissions as osf_permissions


class PreprintPublishedOrAdmin(permissions.BasePermission):

    acceptable_models = (Preprint,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, OsfStorageFolder):
            obj = obj.target
        assert_resource_type(obj, self.acceptable_models)
        auth = get_user_auth(request)
        if request.method in permissions.SAFE_METHODS:
            if auth.user is None:
                return obj.verified_publishable
            else:
                user_has_permissions = (
                    obj.verified_publishable or
                    (obj.is_public and auth.user.has_perm('view_submissions', obj.provider)) or
                    obj.has_permission(auth.user, osf_permissions.ADMIN) or
                    (obj.is_contributor(auth.user) and obj.machine_state != DefaultStates.INITIAL.value)
                )
                return user_has_permissions
        else:
            if not obj.has_permission(auth.user, osf_permissions.ADMIN):
                raise exceptions.PermissionDenied(detail='User must be an admin to make these preprint edits.')
            return True


class PreprintPublishedOrWrite(PreprintPublishedOrAdmin):

    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)

        if isinstance(obj, dict):
            obj = obj.get('self', None)

        if request.method in permissions.SAFE_METHODS:
            return super(PreprintPublishedOrWrite, self).has_object_permission(request, view, obj)
        else:
            if not obj.has_permission(auth.user, osf_permissions.WRITE):
                raise exceptions.PermissionDenied(detail='User must have admin or write permissions to the preprint.')
            return True


class ContributorDetailPermissions(PreprintPublishedOrAdmin):
    """Permissions for preprint contributor detail page."""

    acceptable_models = (Preprint, OSFUser, PreprintContributor)

    def load_resource(self, context, view):
        return Preprint.load(context[view.preprint_lookup_url_kwarg])

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        context = request.parser_context['kwargs']
        preprint = self.load_resource(context, view)
        auth = get_user_auth(request)
        user = OSFUser.load(context['user_id'])

        if request.method in permissions.SAFE_METHODS:
            return super(ContributorDetailPermissions, self).has_object_permission(request, view, preprint)
        elif request.method == 'DELETE':
            return preprint.has_permission(auth.user, osf_permissions.ADMIN) or auth.user == user
        else:
            return preprint.has_permission(auth.user, osf_permissions.ADMIN)


class PreprintIdentifierDetailPermissions(PreprintPublishedOrAdmin):

    acceptable_models = (Identifier, Preprint)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        referent = obj.referent

        if not isinstance(referent, Preprint):
            return True

        return super(PreprintIdentifierDetailPermissions, self).has_object_permission(request, view, referent)


class AdminOrPublic(NodeAdminOrPublic):

    acceptable_models = (Preprint,)


class PreprintFilesPermissions(PreprintPublishedOrAdmin):
    """Permissions for preprint files and provider views."""

    acceptable_models = (Preprint,)

    def load_resource(self, context, view):
        return Preprint.load(context[view.preprint_lookup_url_kwarg])

    def has_object_permission(self, request, view, obj):
        context = request.parser_context['kwargs']
        preprint = self.load_resource(context, view)
        assert_resource_type(preprint, self.acceptable_models)

        if preprint.is_retracted and request.method in permissions.SAFE_METHODS:
            return preprint.can_view_files(get_user_auth(request))

        return super(PreprintFilesPermissions, self).has_object_permission(request, view, preprint)


class ModeratorIfNeverPublicWithdrawn(permissions.BasePermission):
    # Handles case where moderators should be able to see
    # a withdrawn preprint, regardless of "ever_public"
    acceptable_models = (Preprint,)

    def has_object_permission(self, request, view, obj):
        assert_resource_type(obj, self.acceptable_models)
        if not obj.is_retracted:
            return True
        if (obj.is_retracted and obj.ever_public):
            # Tombstone page should be public
            return True

        auth = get_user_auth(request)
        if auth.user is None:
            raise exceptions.NotFound

        if auth.user.has_perm('view_submissions', obj.provider):
            if request.method not in permissions.SAFE_METHODS:
                # Withdrawn preprints should not be editable
                raise exceptions.PermissionDenied(detail='Withdrawn preprints may not be edited')
            return True
        raise exceptions.NotFound
