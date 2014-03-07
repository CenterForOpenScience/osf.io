# -*- coding: utf-8 -*-
import hashlib
from nameparser import HumanName

from website.models import User
from website.util.permissions import reduce_permissions

import logging
logger = logging.getLogger(__name__)

def get_projects(user):
    '''Return a list of user's projects, excluding registrations.'''
    return [
        node
        for node in user.node__contributed
        if node.category == 'project'
        and not node.is_registration
        and not node.is_deleted
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
        'username': user.username,
        'surname': user.family_name,
        'fullname': user.fullname,
        'gravatar_url': user.gravatar_url,
        'active': user.is_active(),
    }
    if node is not None:
        rv.update({
            'permission': reduce_permissions(node.get_permissions(user)),
            'contributions': len([
                log
                for log in node.logs
                if log and log.user == user
            ])
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
