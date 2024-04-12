# -*- coding: utf-8 -*-
from framework import auth

from api.base import settings as api_settings
from website import settings
from osf.models import Contributor, UserQuota
from addons.osfstorage.models import Region
from website.filters import profile_image_url
from osf.utils.permissions import READ
from osf.utils import workflows
from api.waffle.utils import storage_i18n_flag_active
from website.util import quota


def get_profile_image_url(user, size=settings.PROFILE_IMAGE_MEDIUM):
    return profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                             user,
                             use_ssl=True,
                             size=size)

def serialize_user(user, node=None, admin=False, full=False, is_profile=False, include_node_counts=False):
    """
    Return a dictionary representation of a registered user.

    :param User user: A User object
    :param bool full: Include complete user properties
    """
    contrib = None
    if isinstance(user, Contributor):
        contrib = user
        user = contrib.user
    fullname = user.display_full_name(node=node)
    idp_attrs = user.get_idp_attr()
    ret = {
        'id': str(user._id),
        'primary_key': user.id,
        'registered': user.is_registered,
        'surname': user.family_name,
        'fullname': fullname,
        'shortname': fullname if len(fullname) < 50 else fullname[:23] + '...' + fullname[-23:],
        'profile_image_url': user.profile_image_url(size=settings.PROFILE_IMAGE_MEDIUM),
        'active': user.is_active,
        'have_email': user.have_email,
        'idp_email': idp_attrs.get('email'),
    }
    if node is not None:
        if admin:
            flags = {
                'visible': False,
                'permission': READ,
            }
        else:
            if not contrib:
                try:
                    contrib = node.contributor_set.get(user=user)
                except Contributor.NotFoundError:
                    contrib = None
            is_contributor_obj = isinstance(contrib, Contributor)
            flags = {
                'visible': contrib.visible if is_contributor_obj else node.contributor_set.filter(user=user, visible=True).exists(),
                'permission': contrib.permission if is_contributor_obj else None
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

        default_region = user.get_addon('osfstorage').default_region
        available_regions = [region for region in Region.objects.all().values('_id', 'name')]

        storage_type = UserQuota.NII_STORAGE
        institution = user.affiliated_institutions.first()
        if institution is not None and Region.objects.filter(_id=institution._id).exists():
            storage_type = UserQuota.CUSTOM_STORAGE

        max_quota, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = quota.abbreviate_size(used_quota)
        if used_quota_abbr[1] == 'B':
            used_quota_abbr = '{:.0f}[{}]'.format(used_quota_abbr[0], used_quota_abbr[1])
        else:
            size_unit = used_quota_abbr[1]
            used_quota_abbr = '{:.1f}[{}]'.format(used_quota_abbr[0], size_unit)

        if max_quota == 0:
            used_rate = float(used_quota) / float(used_quota)
        else:
            used_rate = float(used_quota) / (max_quota * api_settings.SIZE_UNIT_GB)
        icon_name = None
        if used_rate < api_settings.WARNING_THRESHOLD:
            icon_name = 'storage_ok.png'
        elif used_rate < 1.0:
            icon_name = 'storage_warning.png'
        else:
            icon_name = 'storage_error.png'

        ret.update({
            'activity_points': user.get_activity_points(),
            'profile_image_url': user.profile_image_url(size=settings.PROFILE_IMAGE_LARGE),
            'is_merged': user.is_merged,
            'available_regions': available_regions,
            'storage_flag_is_active': storage_i18n_flag_active(),
            'default_region': {'name': default_region.name, '_id': default_region._id},
            'merged_by': merged_by,
            'quota': {
                'max': max_quota,
                'used': used_quota_abbr,
                'rate': '{:.1f}'.format(used_rate * 100),
                'icon_url': '{}static/img/{}'.format(settings.DOMAIN, icon_name),
                'is_nii_storage': storage_type == UserQuota.NII_STORAGE
            }
        })
        if include_node_counts:
            projects = user.nodes.exclude(is_deleted=True).filter(type='osf.node').get_roots()
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
        'profile_image_url': user.profile_image_url(size=settings.PROFILE_IMAGE_MEDIUM),
        'profile_url': user.profile_url
    }

    if node:
        contributor_info = user.contributor_set.get(node=node.parent_node)
        contributor_json['permission'] = contributor_info.permission
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
            'profile_image_url': profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                                   email,
                                                   use_ssl=True,
                                                   size=settings.PROFILE_IMAGE_MEDIUM),
            'email': email,
        }
    else:
        serialized = add_contributor_json(user)
        serialized['fullname'] = fullname
        serialized['email'] = email
    return serialized


def serialize_access_requests(node):
    """Serialize access requests for a node"""
    return [
        {
            'user': serialize_user(access_request.creator),
            'comment': access_request.comment,
            'id': access_request._id
        } for access_request in node.requests.filter(
            request_type=workflows.RequestTypes.ACCESS.value,
            machine_state=workflows.DefaultStates.PENDING.value
        ).select_related('creator')
    ]
