#!/usr/bin/env python
# encoding: utf-8

import os
import httplib
import logging
import urlparse
import itertools

import furl
import requests
import markupsafe
import simplejson

from modularodm import Q
from cloudstorm import sign

from framework.exceptions import HTTPError

from website.util import rubeus
from website.project.views.file import get_cache_content

from website.addons.osfstorage import model
from website.addons.osfstorage import settings


logger = logging.getLogger(__name__)

url_signer = sign.Signer(
    settings.URLS_HMAC_SECRET,
    settings.URLS_HMAC_DIGEST,
)
webhook_signer = sign.Signer(
    settings.WEBHOOK_HMAC_SECRET,
    settings.WEBHOOK_HMAC_DIGEST,
)


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


def build_hgrid_urls(item, node):
    if isinstance(item, model.OsfStorageFileTree):
        return {
            'upload': node.api_url_for(
                'osf_storage_request_upload_url',
                path=item.path,
            ),
            'fetch': node.api_url_for(
                'osf_storage_hgrid_contents',
                path=item.path,
            ),
        }
    return {
        'view': node.web_url_for(
            'osf_storage_view_file',
            path=item.path,
        ),
        'download': node.web_url_for(
            'osf_storage_view_file',
            path=item.path,
            action='download',
        ),
        'delete': node.api_url_for(
            'osf_storage_delete_file',
            path=item.path,
        ),
    }


def serialize_metadata_hgrid(item, node, permissions):
    """Build HGrid JSON for folder or file. Note: include node URLs for client-
    side URL creation for uploaded files.

    :param item: `FileTree` or `FileRecord` to serialize
    :param Node node: Root node to which the item is attached
    :param dict permissions: Permissions data from `get_permissions`
    """
    return {
        'addon': 'osfstorage',
        # Must escape names rendered by HGrid
        'path': markupsafe.escape(item.path),
        'name': markupsafe.escape(item.name),
        'ext': item.extension,
        rubeus.KIND: get_item_kind(item),
        'urls': build_hgrid_urls(item, node),
        'permissions': permissions,
        'nodeUrl': node.url,
        'nodeApiUrl': node.api_url,
        'downloads': item.get_download_count(),
    }


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
        'date': (
            version.date_created.isoformat()
            if not version.pending
            else None
        ),
        'downloads': record.get_download_count(version=index),
        'urls': {
            'view': node.web_url_for(
                'osf_storage_view_file',
                path=record.path,
                version=index,
            ),
            'download': node.web_url_for(
                'osf_storage_view_file',
                path=record.path,
                version=index,
                action='download',
            ),
        },
    }


chooser = itertools.cycle(settings.UPLOAD_SERVICE_URLS)
def choose_upload_url():
    return next(chooser)


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


def make_signed_request(method, url, signer, payload):
    """Make a signed request to the upload service.

    :param str method: HTTP method
    :param str url: URL to send to
    :param Signer signer: Signed URL signer
    :param dict payload: Data to send
    :raise: `HTTPError` if request fails
    """
    signature, body = sign.build_hook_body(signer, payload)
    try:
        resp = requests.request(
            method,
            url,
            data=body,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                settings.SIGNATURE_HEADER_KEY: signature,
            },
            **settings.SIGNED_REQUEST_KWARGS
        )
    except requests.exceptions.RequestException as error:
        logger.exception(error)
        raise SIGNED_REQUEST_ERROR
    try:
        return resp.json()
    except (TypeError, ValueError, simplejson.JSONDecodeError):
        raise SIGNED_REQUEST_ERROR


def patch_url(url, **kwargs):
    parsed = furl.furl(url)
    for key, value in kwargs.iteritems():
        setattr(parsed, key, value)
    return parsed.url


def ensure_domain(url):
    return patch_url(url, host=settings.DOMAIN)


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


def get_upload_url(node, user, size, content_type, file_path):
    """Request signed upload URL from upload service.

    :param Node node: Root node
    :param User user: User uploading file
    :param int size: Expected file size
    :param str content_type: Expected file content type
    :param str file_path: Expected file path
    """
    payload = {
        'size': size,
        'type': content_type,
        'path': file_path,
        'extra': {'user': user._id},
    }
    urls = build_callback_urls(node, file_path)
    payload.update(urls)
    data = make_signed_request(
        'post',
        urlparse.urljoin(
            choose_upload_url(),
            'urls/upload/',
        ),
        signer=url_signer,
        payload=payload,
    )
    return data['url']


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


def get_download_url(version_idx, file_version, file_record):
    """Request signed download URL from upload service.

    :param FileVersion file_version: Version to fetch
    :param FileRecord file_record: Root file object
    """
    payload = {
        'location': file_version.location,
        'filename': get_filename(version_idx, file_version, file_record),
    }
    data = make_signed_request(
        'POST',
        urlparse.urljoin(
            choose_upload_url(),
            'urls/download/',
        ),
        signer=url_signer,
        payload=payload,
    )
    return data['url']


def get_cache_filename(file_version):
    """Get path to cached rendered file on disk.

    :param FileVersion file_version: Version to locate
    """
    return '{0}.html'.format(file_version.location_hash)


def render_file(version_idx, file_version, file_record):
    """
    :param int version_idx: One-based version index
    :param FileVersion file_version: File version to render
    :param FileRecord file_record: Base file object
    """
    file_obj = model.OsfStorageGuidFile.find_one(
        Q('node', 'eq', file_record.node) &
        Q('path', 'eq', file_record.path)
    )
    cache_file_name = get_cache_filename(file_version)
    node_settings = file_obj.node.get_addon('osfstorage')
    rendered = get_cache_content(node_settings, cache_file_name)
    if rendered is None:
        download_url = get_download_url(version_idx, file_version, file_record)
        file_response = requests.get(download_url)
        rendered = get_cache_content(
            node_settings,
            cache_file_name,
            start_render=True,
            remote_path=file_obj.path,
            file_content=file_response.content,
            download_url=file_obj.get_download_path(version_idx),
        )
    return rendered
