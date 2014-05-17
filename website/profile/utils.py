# -*- coding: utf-8 -*-

import logging

import framework
from website.util.permissions import reduce_permissions
from website.filters import gravatar
from website import settings

logger = logging.getLogger(__name__)

def get_projects(user):
    '''Return a list of user's projects, excluding registrations and folders.'''
    return [
        node
        for node in user.node__contributed
        if node.category == 'project'
        and not node.is_registration
        and not node.is_deleted
        and not node.is_folder
    ]


def get_public_projects(user):
    '''Return a list of a user's public projects.'''
    return [p for p in get_projects(user) if p.is_public]


def serialize_user(user, node=None, full=False):
    """Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties

    """
    rv = {
        'id': str(user._primary_key),
        'registered': user.is_registered,
        'surname': user.family_name,
        'fullname': user.display_full_name(node=node),
        'gravatar_url': user.gravatar_url,
        'active': user.is_active(),
    }
    if node is not None:
        rv.update({
            'permission': reduce_permissions(node.get_permissions(user)),
        })
    if user.is_registered:
        rv.update({
            'url': user.url,
            'absolute_url': user.absolute_url,
            'display_absolute_url': user.display_absolute_url,
            'date_registered': user.date_registered.strftime("%Y-%m-%d"),
        })

    if full:
        if user.is_merged:
            merger = user.merged_by
            merged_by = {
                'id': str(merger._primary_key),
                'url': merger.url,
                'absolute_url': merger.absolute_url
            }
        else:
            merged_by = None
        rv.update({
            'number_projects': len(get_projects(user)),
            'number_public_projects': len(get_public_projects(user)),
            'activity_points': user.activity_points,
            'gravatar_url': user.gravatar_url,
            'is_merged': user.is_merged,
            'merged_by': merged_by,
        })

    return rv


def serialize_contributors(contribs, node):

    return [
        serialize_user(contrib, node)
        for contrib in contribs
    ]


def add_contributor_json(user):
    return {
        'fullname': user.fullname,
        'email': user.username,
        'id': user._primary_key,
        'registered': user.is_registered,
        'active': user.is_active(),
        'gravatar_url': gravatar(
            user, use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        ),
    }

def serialize_unregistered(fullname, email):
    """Serializes an unregistered user.
    """
    user = framework.auth.get_user(username=email)
    if user is None:
        serialized = {
            'fullname': fullname,
            'id': None,
            'registered': False,
            'active': False,
            'gravatar': gravatar(email, use_ssl=True,
                size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR),
            'email': email,
        }
    else:
        serialized = add_contributor_json(user)
        serialized['fullname'] = fullname
        serialized['email'] = email
    return serialized
