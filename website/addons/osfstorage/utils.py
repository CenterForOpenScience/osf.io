# -*- coding: utf-8 -*-

import os
import urlparse

import requests

from cloudstorm import sign

from framework.analytics import get_basic_counters

from website.util import rubeus
from website.project.views.file import get_cache_content

from website.addons.osfstorage import model
from website.addons.osfstorage import settings as osf_storage_settings


url_signer = sign.Signer(
    osf_storage_settings.URLS_HMAC_SECRET,
    osf_storage_settings.URLS_HMAC_DIGEST,
)
webhook_signer = sign.Signer(
    osf_storage_settings.WEBHOOK_HMAC_SECRET,
    osf_storage_settings.WEBHOOK_HMAC_DIGEST,
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
    if isinstance(item, model.FileTree):
        return rubeus.FOLDER
    if isinstance(item, model.FileRecord):
        return rubeus.FILE
    raise TypeError('Value must be instance of `FileTree` or `FileRecord`')


def build_hgrid_urls(item, node):
    if isinstance(item, model.FileTree):
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
            'osf_storage_download_file',
            path=item.path,
        ),
        'delete': node.api_url_for(
            'osf_storage_delete_file',
            path=item.path,
        ),
    }


def get_download_count(item, node, version_idx=None):
    """
    :param item: `FileTree` or `FileRecord` to look up
    :param Node node: Root node to which the item is attached
    :param int version_idx: Optional one-based version index
    """
    if isinstance(item, model.FileTree):
        return None
    parts = ['download', node._id, item.path]
    if version_idx is not None:
        parts.append(version_idx)
    page = ':'.join([format(part) for part in parts])
    _, count = get_basic_counters(page)
    return count or 0


def serialize_metadata_hgrid(item, node, permissions):
    """Build HGrid JSON for folder or file. Note: include node URLs for client-
    side URL creation for uploaded files.

    :param item: `FileTree` or `FileRecord` to serialize
    :param Node node: Root node to which the item is attached
    :param dict permissions: Permissions data from `get_permissions`
    """
    return {
        'addon': 'osfstorage',
        'path': item.path,
        'name': item.name,
        'ext': item.extension,
        rubeus.KIND: get_item_kind(item),
        'urls': build_hgrid_urls(item, node),
        'permissions': permissions,
        'nodeUrl': node.url,
        'nodeApiUrl': node.api_url,
        'downloads': get_download_count(item, node),
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
        'date': version.date_modified.isoformat(),
        'urls': {
            'view': node.web_url_for(
                'osf_storage_view_file',
                path=record.path,
                version=index,
            ),
            'download': node.web_url_for(
                'osf_storage_download_file',
                path=record.path,
                version=index,
            ),
        },
    }


def get_file_name(path):
    return os.path.basename(path.strip('/'))


def make_signed_request(method, url, signer, payload):
    """
    """
    signature, body = sign.build_hook_body(signer, payload)
    resp = requests.request(
        method,
        url,
        data=body,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            osf_storage_settings.SIGNATURE_HEADER_KEY: signature,
        },
    )
    return resp.json()


def build_callback_urls(node, path):
    return {
        'startUrl': node.api_url_for(
            'osf_storage_upload_start_hook',
            path=path,
            _external=True,
        ),
        'finishUrl': node.api_url_for(
            'osf_storage_upload_finish_hook',
            path=path,
            _external=True,
        ),
    }


def get_upload_url(node, user, size, content_type, file_path):
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
            osf_storage_settings.UPLOAD_SERVICE_URL,
            'urls/upload/',
        ),
        signer=url_signer,
        payload=payload,
    )
    return data['url']


def get_download_url(file_version):
    """
    :param FileVersion file_version: Version to fetch
    """
    payload = {'location': file_version.location}
    signature, body = sign.build_hook_body(url_signer, payload)
    data = make_signed_request(
        'POST',
        urlparse.urljoin(
            osf_storage_settings.UPLOAD_SERVICE_URL,
            'urls/download/',
        ),
        signer=url_signer,
        payload=payload,
    )
    return data['url']


def get_cache_filename(file_version):
    """
    :param FileVersion file_version: Version to locate
    """
    return '{0}.html'.format(file_version.location_hash)


def render_file(file_obj, file_version, version_idx):
    """
    :param StorageFile file_obj: Base file object to render
    :param FileVersion file_version: File version to render
    :param int version_idx: One-based version index
    """
    cache_filename = get_cache_filename(file_version)
    node_settings = file_obj.node.get_addon('osfstorage')
    rendered = get_cache_content(node_settings, cache_filename)
    if rendered is None:
        download_url = get_download_url(file_version)
        file_response = requests.get(download_url)
        rendered = get_cache_content(
            node_settings=node_settings,
            cache_file=cache_filename,
            start_render=True,
            file_path=get_file_name(file_obj.path),
            file_content=file_response.content,
            download_path=file_obj.get_download_path(version_idx),
        )
    return rendered
