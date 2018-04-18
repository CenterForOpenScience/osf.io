# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import remove_perm
from rest_framework import permissions as drf_permissions

from api.base.utils import get_user_auth

# Object-level permissions for providers.
# Prefer assigning object permissions to groups and adding users to groups, over assigning permissions to users.
PERMISSIONS = {
    'set_up_moderation': 'Can set up moderation for this provider',
    'view_submissions': 'Can view all submissions to this provider',
    'accept_submissions': 'Can accept submissions to this provider',
    'reject_submissions': 'Can reject submissions to this provider',
    'edit_review_comments': 'Can edit comments on actions for this provider',
    'view_actions': 'Can view actions on submissions to this provider',

    'add_moderator': 'Can add other users as moderators for this provider',
    'update_moderator': 'Can elevate or lower other moderators/admins',
    'remove_moderator': 'Can remove moderators from this provider. Implicitly granted to self',

    # TODO Implement editing settings, assign this to admin groups
    'edit_reviews_settings': 'Can edit reviews settings for this provider',

    # TODO Implement reviewers, review workflows, use these permissions
    'add_reviewer': 'Can add other users as reviewers for this provider',
    'assign_reviewer': 'Can assign reviewers to review specific submissions to this provider',
    'view_assigned_submissions': 'Can view submissions to this provider which have been assigned to this user',
    'review_assigned_submissions': 'Can submit reviews for submissions to this provider which have been assigned to this user',
}

# Groups created for each provider.
GROUP_FORMAT = 'reviews_{provider_id}_{group}'
GROUPS = {
    'admin': ('set_up_moderation', 'add_moderator', 'update_moderator', 'remove_moderator', 'view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_actions'),
    'moderator': ('view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_actions'),
    # 'manager': (),  # TODO "Senior editor"-like role, can add/remove/assign moderators and reviewers
    # 'reviewer': (),  # TODO Implement reviewers
}

class GroupHelper(object):
    """Helper for managing permission groups for a given provider.
    """

    def __init__(self, provider):
        self.provider = provider

    def format_group(self, name):
        if name not in GROUPS:
            raise ValueError('Invalid reviews group: "{}"'.format(name))
        return GROUP_FORMAT.format(provider_id=self.provider._id, group=name)

    def get_group(self, name):
        return Group.objects.get(name=self.format_group(name))

    def update_provider_auth_groups(self):
        for group_name, group_permissions in GROUPS.items():
            group, created = Group.objects.get_or_create(name=self.format_group(group_name))
            to_remove = set(get_perms(group, self.provider)).difference(group_permissions)
            for p in to_remove:
                remove_perm(p, group, self.provider)
            for p in group_permissions:
                assign_perm(p, group, self.provider)

    def get_permissions(self, user):
        return [p for p in get_perms(user, self.provider) if p in PERMISSIONS]

class CanSetUpProvider(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in drf_permissions.SAFE_METHODS:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('set_up_moderation', obj)

class CanAddModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('add_moderator', view.get_provider())

class CanDeleteModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method != 'DELETE':
            return True
        auth = get_user_auth(request)
        provider = view.get_provider()
        return auth.user.has_perm('remove_moderator', provider) or auth.user._id == view.kwargs.get('moderator_id', '')

class CanUpdateModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method not in ['PATCH', 'PUT']:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('update_moderator', view.get_provider())

class MustBeModerator(drf_permissions.BasePermission):
    def has_permission(self, request, view):
        auth = get_user_auth(request)
        return bool(get_perms(auth.user, view.get_provider()))
