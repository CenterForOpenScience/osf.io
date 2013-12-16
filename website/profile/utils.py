# -*- coding: utf-8 -*-
import hashlib


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


def serialize_user(user, full=False):
    """Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties

    """
    rv = {
        'id': str(user._primary_key),
        'url': user.url,
        'absolute_url': user.absolute_url,
        'display_absolute_url': user.display_absolute_url,
        'date_registered': user.date_registered.strftime("%Y-%m-%d"),
        'registered': user.is_registered,
        'username': user.username,
        'fullname': user.fullname,
    }

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


def serialize_unreg_user(user):
    '''Return a formatted dictionary representation of a an unregistered user.

    :param dict user: An unregistered user object
    '''
    return {
        'id': hashlib.md5(user['nr_email']).hexdigest(),
        'fullname': user['nr_name'],
        'registered': False,
    }
