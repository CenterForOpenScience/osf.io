# -*- coding: utf-8 -*-

from modularodm import Q

from framework import auth

from website import settings
from website.filters import gravatar
from website.project.model import Node
from website.mailing_list.utils import get_recipients
from website.util.permissions import reduce_permissions


def get_projects(user):
    """Return a list of user's projects, excluding registrations and folders."""
    # Note: If the user is a contributor to a child (but does not have access to the parent), it will be
    # excluded from this view
    # Avoid circular import
    from website.project.utils import TOP_LEVEL_PROJECT_QUERY

    return Node.find_for_user(user, subquery=TOP_LEVEL_PROJECT_QUERY)

def get_public_projects(user):
    """Return a list of a user's public projects."""
    # Avoid circular import
    from website.project.utils import TOP_LEVEL_PROJECT_QUERY

    return Node.find_for_user(
        user,
        subquery=(
            Q('is_public', 'eq', True) &
            TOP_LEVEL_PROJECT_QUERY
        )
    )


def get_gravatar(user, size=None):
    if size is None:
        size = settings.PROFILE_IMAGE_LARGE
    return gravatar(
        user, use_ssl=True,
        size=size
    )


def serialize_user(user, node=None, admin=False, full=False, is_profile=False):
    """
    Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties
    """
    fullname = user.display_full_name(node=node)
    ret = {
        'id': str(user._primary_key),
        'registered': user.is_registered,
        'surname': user.family_name,
        'fullname': fullname,
        'shortname': fullname if len(fullname) < 50 else fullname[:23] + "..." + fullname[-23:],
        'gravatar_url': gravatar(
            user, use_ssl=True,
            size=settings.PROFILE_IMAGE_MEDIUM
        ),
        'active': user.is_active,
    }
    if node is not None:
        if admin:
            flags = {
                'visible': False,
                'permission': 'read',
                'subscribed': False,
            }
        else:
            flags = {
                'visible': user._id in node.visible_contributor_ids,
                'permission': reduce_permissions(node.get_permissions(user)),
                'subscribed': user in get_recipients(node),
            }
        ret.update(flags)
    if user.is_registered:
        ret.update({
            'url': user.url,
            'absolute_url': user.absolute_url,
            'display_absolute_url': user.display_absolute_url,
            'date_registered': user.date_registered.strftime("%Y-%m-%d"),
        })

    if full:
        # Add emails
        if is_profile:
            ret['emails'] = [
                {
                    'address': each,
                    'primary': each.strip().lower() == user.username.strip().lower(),
                    'confirmed': True,
                } for each in user.emails
            ] + [
                {
                    'address': each,
                    'primary': each.strip().lower() == user.username.strip().lower(),
                    'confirmed': False
                }
                for each in user.unconfirmed_emails
            ]

        if user.is_merged:
            merger = user.merged_by
            merged_by = {
                'id': str(merger._primary_key),
                'url': merger.url,
                'absolute_url': merger.absolute_url
            }
        else:
            merged_by = None
        ret.update({
            'number_projects': get_projects(user).count(),
            'number_public_projects': get_public_projects(user).count(),
            'activity_points': user.get_activity_points(),
            'gravatar_url': gravatar(
                user, use_ssl=True,
                size=settings.PROFILE_IMAGE_LARGE
            ),
            'is_merged': user.is_merged,
            'merged_by': merged_by,
        })

    return ret


def serialize_contributors(contribs, node, **kwargs):
    return [
        serialize_user(contrib, node, **kwargs)
        for contrib in contribs
    ]


def add_contributor_json(user, current_user=None):
    """
    Generate a dictionary representation of a user, optionally including # projects shared with `current_user`

    :param User user: The user object to serialize
    :param User current_user : The user object for a different user, to calculate number of projects in common
    :return dict: A dict representing the serialized user data
    """
    # get shared projects
    if current_user:
        n_projects_in_common = current_user.n_projects_in_common(user)
    else:
        n_projects_in_common = 0

    current_employment = None
    education = None

    if user.jobs:
        current_employment = user.jobs[0]['institution']

    if user.schools:
        education = user.schools[0]['institution']

    return {
        'fullname': user.fullname,
        'email': user.username,
        'id': user._primary_key,
        'employment': current_employment,
        'education': education,
        'n_projects_in_common': n_projects_in_common,
        'registered': user.is_registered,
        'active': user.is_active,
        'gravatar_url': gravatar(
            user, use_ssl=True,
            size=settings.PROFILE_IMAGE_MEDIUM
        ),
        'profile_url': user.profile_url
    }

def serialize_unregistered(fullname, email):
    """Serializes an unregistered user."""
    user = auth.get_user(email=email)
    if user is None:
        serialized = {
            'fullname': fullname,
            'id': None,
            'registered': False,
            'active': False,
            'gravatar': gravatar(email, use_ssl=True,
                                 size=settings.PROFILE_IMAGE_MEDIUM),
            'email': email,
        }
    else:
        serialized = add_contributor_json(user)
        serialized['fullname'] = fullname
        serialized['email'] = email
    return serialized
