# -*- coding: utf-8 -*-

import os
import httplib
import logging

import furl
import itsdangerous
from modularodm import Q
from flask import request

from framework.exceptions import HTTPError

from website import settings as site_settings

from website.util import rubeus
from website.models import Session

from website.addons.osfstorage import model

logger = logging.getLogger(__name__)


def get_permissions(auth, node):
    """Get editing and viewing permissions.

    :param Auth auth: Consolidated auth
    :param Node node: Node to check
    """
    return {
        'edit': node.can_edit(auth) and not node.is_registration,
        'view': node.can_view(auth),
    }


def get_item_kind(item):
    if isinstance(item, model.OsfStorageFileTree):
        return rubeus.FOLDER
    if isinstance(item, model.OsfStorageFileRecord):
        return rubeus.FILE
    raise TypeError('Value must be instance of `FileTree` or `FileRecord`')


def serialize_metadata_hgrid(item, node):
    """Build HGrid JSON for folder or file. Note: include node URLs for client-
    side URL creation for uploaded files.

    :param item: `FileTree` or `FileRecord` to serialize
    :param Node node: Root node to which the item is attached
    :param dict permissions: Permissions data from `get_permissions`
    """
    ret = {
        'path': item.path,
        'name': item.name,
        'ext': item.extension,
        rubeus.KIND: get_item_kind(item),
        'downloads': item.get_download_count(),
    }

    if isinstance(item, model.OsfStorageFileRecord):
        ret['version'] = len(item.versions)

    return ret


def serialize_revision(node, record, version, index):
    """Serialize revision for use in revisions table.

    :param Node node: Root node
    :param FileRecord record: Root file record
    :param FileVersion version: The version to serialize
    :param int index: One-based index of version
    """
    return {
        'index': index,
        'user': {
            'name': version.creator.fullname,
            'url': version.creator.url,
        },
        'date': version.date_created.isoformat(),
        'downloads': record.get_download_count(version=index),
    }


SIGNED_REQUEST_ERROR = HTTPError(
    httplib.SERVICE_UNAVAILABLE,
    data={
        'message_short': 'Upload service unavailable',
        'message_long': (
            'Upload service is not available; please retry '
            'your upload in a moment'
        ),
    },
)


def patch_url(url, **kwargs):
    parsed = furl.furl(url)
    for key, value in kwargs.iteritems():
        setattr(parsed, key, value)
    return parsed.url


def ensure_domain(url):
    return patch_url(url, host=site_settings.DOMAIN)


def build_callback_urls(node, path):
    start_url = node.api_url_for('osf_storage_upload_start_hook', path=path)
    finish_url = node.api_url_for('osf_storage_upload_finish_hook', path=path)
    cached_url = node.api_url_for('osf_storage_upload_cached_hook', path=path)
    ping_url = node.api_url_for('osf_storage_upload_ping_hook', path=path)
    archive_url = node.api_url_for('osf_storage_upload_archived_hook', path=path)
    return {
        'startUrl': ensure_domain(start_url),
        'finishUrl': ensure_domain(finish_url),
        'cachedUrl': ensure_domain(cached_url),
        'pingUrl': ensure_domain(ping_url),
        'archiveUrl': ensure_domain(archive_url),
    }


def get_filename(version_idx, file_version, file_record):
    """Build name for downloaded file, appending version date if not latest.

    :param int version_idx: One-based version index
    :param FileVersion file_version: Version to name
    :param FileRecord file_record: Root file object
    """
    if version_idx == len(file_record.versions):
        return file_record.name
    name, ext = os.path.splitext(file_record.name)
    return u'{name}-{date}{ext}'.format(
        name=name,
        date=file_version.date_created.isoformat(),
        ext=ext,
    )


def get_cookie_for_user(user):
    sessions = Session.find(
        Q('data.auth_user_id', 'eq', user._id)
    ).sort(
        '-date_modified'
    )
    if sessions:
        session = sessions[0]
    else:
        session = Session(data={
            'auth_user_id': user._id,
            'auth_user_username': user.username,
            'auth_user_fullname': user.fullname,
        })
        session.save()
    signer = itsdangerous.Signer(site_settings.SECRET_KEY)
    return signer.sign(session._id)


def get_waterbutler_url(user, *path, **query):
    url = furl.furl(site_settings.WATERBUTLER_URL)
    url.path.segments.extend(path)
    cookie = (
        get_cookie_for_user(user)
        if user
        else request.cookies.get(site_settings.COOKIE_NAME)
    )
    url.args.update({
        'provider': 'osfstorage',
        'cookie': cookie,
    })
    if 'view_only' in request.args:
        url.args['view_only'] = request.args['view_only']
    url.args.update(query)
    return url.url


def get_waterbutler_download_url(version_idx, file_version, file_record, user=None, **query):
    nid = file_record.node._id
    display_name = get_filename(version_idx, file_version, file_record)
    return get_waterbutler_url(
        user,
        'file',
        nid=nid,
        path='/' + file_record.name,
        displayName=display_name,
        version=version_idx,
        **query
    )


def get_waterbutler_upload_url(user, node, path, **query):
    return get_waterbutler_url(user, 'file', nid=node._id, path=path, **query)
