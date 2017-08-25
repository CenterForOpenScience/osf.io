# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import remove_perm
from rest_framework import exceptions, permissions

from django.contrib.auth.models import Group

from api.base.exceptions import Conflict
from api.base.utils import get_user_auth
from website.util import permissions as osf_permissions

from reviews import models
from reviews.workflow import Actions


logger = logging.getLogger(__name__)


# Object-level permissions for providers.
# Prefer assigning object permissions to groups and adding users to groups, over assigning permissions to users.
PERMISSIONS = {
    'set_up_moderation': 'Can set up moderation for this provider',
    'view_submissions': 'Can view all submissions to this provider',
    'accept_submissions': 'Can accept submissions to this provider',
    'reject_submissions': 'Can reject submissions to this provider',
    'edit_review_comments': 'Can edit comments on review logs for this provider',
    'view_review_logs': 'Can view review/moderation logs for submissions to this provider',

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
    'admin': ('set_up_moderation', 'add_moderator', 'view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_review_logs'),
    'moderator': ('view_submissions', 'accept_submissions', 'reject_submissions', 'edit_review_comments', 'view_review_logs'),
    'manager': (),  # TODO "Senior editor"-like role, can add/remove/assign moderators and reviewers
    'reviewer': (),  # TODO Implement reviewers
}


# Required permission to perform each action. `None` means no permissions required.
ACTION_PERMISSIONS = {
    Actions.SUBMIT.value: None,
    Actions.ACCEPT.value: 'accept_submissions',
    Actions.REJECT.value: 'reject_submissions',
    Actions.EDIT_COMMENT.value: 'edit_review_comments',
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
            if created:
                logger.debug('Created group %s', group.name)
            to_remove = set(get_perms(group, self.provider)).difference(group_permissions)
            for p in to_remove:
                remove_perm(p, group, self.provider)
                logger.debug('Removed permission %s from group %s for provider %s', p, group.name, self.provider._id)
            for p in group_permissions:
                assign_perm(p, group, self.provider)
                logger.debug('Assigned permission %s to group %s for provider %s', p, group.name, self.provider._id)

    def get_permissions(self, user):
        return [p for p in get_perms(user, self.provider) if p in PERMISSIONS]


class LogPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        auth = get_user_auth(request)
        if auth.user is None:
            return False

        reviewable = None
        provider = None
        if isinstance(obj, models.ReviewLog):
            reviewable = obj.reviewable
            provider = reviewable.provider
        elif isinstance(obj, models.ReviewableMixin):
            reviewable = obj
            provider = reviewable.provider
        elif isinstance(obj, models.ReviewProviderMixin):
            provider = obj
        else:
            raise ValueError('Not a reviews-related model: {}'.format(obj))

        is_node_admin = reviewable is not None and reviewable.node.has_permission(auth.user, osf_permissions.ADMIN)

        if request.method in permissions.SAFE_METHODS:
            # If the provider settings allow it, let preprint admins see logs for their submission
            return (is_node_admin and reviewable.provider.reviews_comments_private is False) or auth.user.has_perm('view_review_logs', provider)
        else:
            # Moderators and node admins can trigger state changes.
            # Action-specific permissions should be checked in the view.
            return is_node_admin or auth.user.has_perm('view_submissions', provider)


class CanSetUpProvider(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        auth = get_user_auth(request)
        return auth.user.has_perm('set_up_moderation', obj)
