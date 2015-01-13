# -*- coding: utf-8 -*-
import framework
from website.util.permissions import reduce_permissions
from website.filters import gravatar
from website import settings


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
    fullname = user.display_full_name(node=node)
    rv = {
        'id': str(user._primary_key),
        'registered': user.is_registered,
        'surname': user.family_name,
        'fullname': fullname,
        'shortname': fullname if len(fullname) < 50 else fullname[:23] + "..." + fullname[-23:],
        'gravatar_url': gravatar(
            user, use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        ),
        'active': user.is_active,
    }
    if node is not None:
        rv.update({
            'visible': user._id in node.visible_contributor_ids,
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
            'activity_points': user.get_activity_points(),
            'gravatar_url': gravatar(
                user, use_ssl=True,
                size=settings.GRAVATAR_SIZE_PROFILE
            ),
            'is_merged': user.is_merged,
            'merged_by': merged_by,
        })

    return rv


def serialize_contributors(contribs, node):

    return [
        serialize_user(contrib, node)
        for contrib in contribs
    ]


def add_contributor_json(user, current_user=None):

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
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        ),
        'profile_url': user.profile_url
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
