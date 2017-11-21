# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import remove_perm
from rest_framework import permissions as drf_permissions

from django.contrib.auth.models import Group

from api.base.utils import get_user_auth
from osf.models.action import Action
from website.util import permissions as osf_permissions

from reviews.models import ReviewableMixin, ReviewProviderMixin
from reviews.workflow import Triggers


logger = logging.getLogger(__name__)


# Object-level permissions for providers.
# Prefer assigning object permissions to groups and adding users to groups, over assigning permissions to users.
PERMISSIONS = {
    'set_up_moderation': 'Can set up moderation for this provider',
    'view_submissions': 'Can view all submissions to this provider',
    'accept_submissions': 'Can accept submissions to this provider',
    'reject_submissions': 'Can reject submissions to this provider',
    'edit_review_comments': 'Can edit comments on actions for this provider',
    'view_actions': 'Can view actions on submissions to this provider',

    # TODO Implement adding/removing moderators via API. Currently must be done in OSF Admin
    'add_moderator': 'Can add other users as moderators for this provider',

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
    'admin': ('set_up_moderation', 'add_moderator', 'view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_actions'),
    'moderator': ('view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_actions'),
    # 'manager': (),  # TODO "Senior editor"-like role, can add/remove/assign moderators and reviewers
    # 'reviewer': (),  # TODO Implement reviewers
}


# Required permission to perform each action. `None` means no permissions required.
TRIGGER_PERMISSIONS = {
    Triggers.SUBMIT.value: None,
    Triggers.ACCEPT.value: 'accept_submissions',
    Triggers.REJECT.value: 'reject_submissions',
    Triggers.EDIT_COMMENT.value: 'edit_review_comments',
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


class ActionPermission(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user is None:
            return False

        target = None
        provider = None
        if isinstance(obj, Action):
            target = obj.target
            provider = target.provider
        elif isinstance(obj, ReviewableMixin):
            target = obj
            provider = target.provider
        elif isinstance(obj, ReviewProviderMixin):
            provider = obj
        else:
            raise ValueError('Not a reviews-related model: {}'.format(obj))

        serializer = view.get_serializer()

        if request.method in drf_permissions.SAFE_METHODS:
            # Moderators and node contributors can view actions
            is_node_contributor = target is not None and target.node.has_permission(auth.user, osf_permissions.READ)
            return is_node_contributor or auth.user.has_perm('view_actions', provider)
        else:
            # Moderators and node admins can trigger state changes.
            is_node_admin = target is not None and target.node.has_permission(auth.user, osf_permissions.ADMIN)
            if not (is_node_admin or auth.user.has_perm('view_submissions', provider)):
                return False

            # User can trigger state changes on this reviewable, but can they use this trigger in particular?
            serializer = view.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            trigger = serializer.validated_data.get('trigger')
            permission = TRIGGER_PERMISSIONS[trigger]
            return permission is None or request.user.has_perm(permission, target.provider)


class CanSetUpProvider(drf_permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in drf_permissions.SAFE_METHODS:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('set_up_moderation', obj)
