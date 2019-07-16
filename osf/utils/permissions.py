# -*- coding: utf-8 -*-

# Permissions
READ = 'read'
WRITE = 'write'
ADMIN = 'admin'
# NOTE: Ordered from most-restrictive to most permissive
READ_NODE = 'read_node'
WRITE_NODE = 'write_node'
ADMIN_NODE = 'admin_node'
PERMISSIONS = [READ_NODE, WRITE_NODE, ADMIN_NODE]
CONTRIB_PERMISSIONS = {ADMIN_NODE: ADMIN, WRITE_NODE: WRITE, READ_NODE: READ}
API_CONTRIBUTOR_PERMISSIONS = [READ, WRITE, ADMIN]
CREATOR_PERMISSIONS = ADMIN
DEFAULT_CONTRIBUTOR_PERMISSIONS = WRITE

# Roles
MANAGER = 'manager'
MEMBER = 'member'

MANAGE = 'manage'
GROUP_ROLES = [MANAGER, MEMBER]

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


def reduce_permissions(permissions):
    """
    Works if technical permissions are passed ['read_node', 'write_node'],
    or short form are passed ['read', 'write']
    """
    for permission in API_CONTRIBUTOR_PERMISSIONS[::-1]:
        if permission in permissions:
            return permission
    for permission in PERMISSIONS[::-1]:
        if permission in permissions:
            return CONTRIB_PERMISSIONS[permission]
    raise ValueError('Permissions not in permissions list')


def check_private_key_for_anonymized_link(private_key):
    from osf.models import PrivateLink
    try:
        link = PrivateLink.objects.get(key=private_key, is_deleted=False)
    except PrivateLink.DoesNotExist:
        return False
    return link.anonymous
