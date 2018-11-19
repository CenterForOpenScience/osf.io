# -*- coding: utf-8 -*-

# Permissions
READ = 'read'
WRITE = 'write'
ADMIN = 'admin'
# NOTE: Ordered from most-restrictive to most permissive
PERMISSIONS = ['read_node', 'write_node', 'admin_node']
CONTRIB_PERMISSIONS = {'admin_node': 'admin', 'write_node': 'write', 'read_node': 'read'}
API_CONTRIBUTOR_PERMISSIONS = [READ, WRITE, ADMIN]
CREATOR_PERMISSIONS = ADMIN
DEFAULT_CONTRIBUTOR_PERMISSIONS = WRITE

# Permissions for ReviewableProviderMixin(GuardianMixin)
REVIEW_PERMISSIONS = (
    ('set_up_moderation', 'Can set up moderation for this provider'),
    ('view_submissions', 'Can view all submissions to this provider'),
    ('accept_submissions', 'Can accept submissions to this provider'),
    ('reject_submissions', 'Can reject submissions to this provider'),
    ('withdraw_submissions', 'Can withdraw submissions from this provider'),
    ('edit_review_comments', 'Can edit comments on actions for this provider'),
    ('view_actions', 'Can view actions on submissions to this provider'),

    ('add_moderator', 'Can add other users as moderators for this provider'),
    ('update_moderator', 'Can elevate or lower other moderators/admins'),
    ('remove_moderator', 'Can remove moderators from this provider. Implicitly granted to self'),

    # TODO Implement editing settings, assign this to admin groups
    ('edit_reviews_settings', 'Can edit reviews settings for this provider'),

    # TODO Implement reviewers, review workflows, use these permissions
    ('add_reviewer', 'Can add other users as reviewers for this provider'),
    ('assign_reviewer', 'Can assign reviewers to review specific submissions to this provider'),
    ('view_assigned_submissions', 'Can view submissions to this provider which have been assigned to this user'),
    ('review_assigned_submissions', 'Can submit reviews for submissions to this provider which have been assigned to this user'),
)

REVIEW_GROUPS = {
    'admin': ('set_up_moderation', 'add_moderator', 'update_moderator', 'remove_moderator', 'view_submissions', 'accept_submissions', 'reject_submissions', 'withdraw_submissions', 'edit_review_comments', 'view_actions'),
    'moderator': ('view_submissions', 'accept_submissions', 'reject_submissions', 'withdraw_submissions', 'edit_review_comments', 'view_actions'),
    # 'manager': (),  # TODO "Senior editor"-like role, can add/remove/assign moderators and reviewers
    # 'reviewer': (),  # TODO Implement reviewers
}

def expand_permissions(permission):
    if not permission:
        return []
    index = PERMISSIONS.index(permission) + 1
    return PERMISSIONS[:index]


def reduce_permissions(permissions):
    for permission in PERMISSIONS[::-1]:
        if permission in permissions:
            return CONTRIB_PERMISSIONS[permission]
    raise ValueError('Permissions not in permissions list')


def check_private_key_for_anonymized_link(private_key):
    from osf.models import PrivateLink
    try:
        link = PrivateLink.objects.get(key=private_key)
    except PrivateLink.DoesNotExist:
        return False
    return link.anonymous
