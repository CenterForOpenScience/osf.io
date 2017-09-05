# -*- coding: utf-8 -*-
from framework import auth

from website import settings
from website.filters import gravatar
from osf.models import Contributor
from osf.models.contributor import get_contributor_permissions
from website.util.permissions import reduce_permissions


def get_gravatar(user, size=None):
    if size is None:
        size = settings.PROFILE_IMAGE_LARGE
    return gravatar(
        user, use_ssl=True,
        size=size
    )


def serialize_user(user, node=None, admin=False, full=False, is_profile=False, include_node_counts=False):
    """
    Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties
    """
    from website.project.utils import PROJECT_QUERY
    contrib = None
    if isinstance(user, Contributor):
        contrib = user
        user = contrib.user
    fullname = user.display_full_name(node=node)
    ret = {
        'id': str(user._id),
        'registered': user.is_registered,
        'surname': user.family_name,
        'fullname': fullname,
        'shortname': fullname if len(fullname) < 50 else fullname[:23] + '...' + fullname[-23:],
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
            }
        else:
            is_contributor_obj = isinstance(contrib, Contributor)
            flags = {
                'visible': contrib.visible if is_contributor_obj else node.contributor_set.filter(user=user, visible=True).exists(),
                'permission': get_contributor_permissions(contrib, as_list=False) if is_contributor_obj else reduce_permissions(node.get_permissions(user)),
            }
        ret.update(flags)
    if user.is_registered:
        ret.update({
            'url': user.url,
            'absolute_url': user.absolute_url,
            'display_absolute_url': user.display_absolute_url,
            'date_registered': user.date_registered.strftime('%Y-%m-%d'),
        })

    if full:
        # Add emails
        if is_profile:
            ret['emails'] = [
                {
                    'address': each,
                    'primary': each.strip().lower() == user.username.strip().lower(),
                    'confirmed': True,
                } for each in user.emails.values_list('address', flat=True)
            ] + [
                {
                    'address': each,
                    'primary': each.strip().lower() == user.username.strip().lower(),
                    'confirmed': False
                }
                for each in user.get_unconfirmed_emails_exclude_external_identity()
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
            'activity_points': user.get_activity_points(),
            'gravatar_url': gravatar(
                user, use_ssl=True,
                size=settings.PROFILE_IMAGE_LARGE
            ),
            'is_merged': user.is_merged,
            'merged_by': merged_by,
        })
        if include_node_counts:
            projects = user.nodes.filter(PROJECT_QUERY).get_roots()
            ret.update({
                'number_projects': projects.count(),
                'number_public_projects': projects.filter(is_public=True).count(),
            })

    return ret


def serialize_contributors(contribs, node, **kwargs):
    return [
        serialize_user(contrib, node, **kwargs)
        for contrib in contribs
    ]


def serialize_visible_contributors(node):
    # This is optimized when node has .include('contributor__user__guids')
    return [
        serialize_user(c, node) for c in node.contributor_set.all() if c.visible
    ]


def add_contributor_json(user, current_user=None, node=None):
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

    contributor_json = {
        'fullname': user.fullname,
        'email': user.email,
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

    if node:
        contributor_info = user.contributor_set.get(node=node.parent_node)
        contributor_json['permission'] = get_contributor_permissions(contributor_info, as_list=False)
        contributor_json['visible'] = contributor_info.visible

    return contributor_json


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
