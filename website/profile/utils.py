# -*- coding: utf-8 -*-
import framework
from framework.auth.utils import privacy_info_handle
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


def get_gravatar(user, size=None):
    if size is None:
        size = settings.GRAVATAR_SIZE_PROFILE
    return gravatar(
        user, use_ssl=True,
        size=size
    )


def serialize_user(user, node=None, admin=False, full=False, n_comments=None, anonymous=False):
    """Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties
    """
    fullname = user.display_full_name(node=node)
    ret = {
        'id': privacy_info_handle(str(user._primary_key), anonymous),
        'registered': user.is_registered,
        'surname': privacy_info_handle(user.family_name, anonymous),
        'fullname': privacy_info_handle(fullname, anonymous, name=True),
        'shortname': privacy_info_handle(fullname if len(fullname) < 50 else fullname[:23] + "..." + fullname[-23:], anonymous),
        'gravatar_url': privacy_info_handle(gravatar(
            user, use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        ), anonymous),
        'active': user.is_active,
    }
    if node is not None:
        ret.update({
            'isContributor': node.is_contributor(user)
        })
        if admin:
            flags = {
                'visible': False,
                'permission': 'read',
            }
        else:
            flags = {
                'visible': user._id in node.visible_contributor_ids,
                'permission': reduce_permissions(node.get_permissions(user)),
            }
        ret.update(flags)
    if user.is_registered:
        ret.update({
            'url': privacy_info_handle(user.url, anonymous),
            'absolute_url': privacy_info_handle(user.absolute_url, anonymous),
            'display_absolute_url': privacy_info_handle(user.display_absolute_url, anonymous),
            'date_registered': user.date_registered.strftime("%Y-%m-%d")
        })

    if full:
        # Add emails
        ret['emails'] = [
            {
                'address': privacy_info_handle(each, anonymous),
                'primary': each == user.username,
                'confirmed': True,
            } for each in user.emails
        ] + [
            {
                'address': privacy_info_handle(each, anonymous),
                'primary': each == user.username,
                'confirmed': False
            }
            for each in user.unconfirmed_emails
        ]

        if user.is_merged:
            merger = privacy_info_handle(user.merged_by, anonymous)
            merged_by = {
                'id': privacy_info_handle(str(merger._primary_key), anonymous),
                'url': privacy_info_handle(merger.url, anonymous),
                'absolute_url': privacy_info_handle(merger.absolute_url, anonymous)
            }
        else:
            merged_by = None
        ret.update({
            'number_projects': len(get_projects(user)),
            'number_public_projects': len(get_public_projects(user)),
            'activity_points': user.get_activity_points(),
            'gravatar_url': privacy_info_handle(gravatar(
                user, use_ssl=True,
                size=settings.GRAVATAR_SIZE_PROFILE
            ), anonymous),
            'is_merged': user.is_merged,
            'merged_by': privacy_info_handle(merged_by, anonymous),
        })

    if n_comments:
        ret.update({
            'numOfComments': n_comments,
            'gravatar_url': privacy_info_handle(gravatar(
                user, use_ssl=True,
                size=settings.GRAVATAR_SIZE_DISCUSSION
            ), anonymous),
        })

    return ret


def serialize_contributors(contribs, node, **kwargs):
    return [
        serialize_user(contrib, node, **kwargs)
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
    user = framework.auth.get_user(email=email)
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
