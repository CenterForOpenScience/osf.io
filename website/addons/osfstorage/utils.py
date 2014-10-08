# -*- coding: utf-8 -*-

import os
import urlparse

import requests

from cloudstorm import sign

from website.util import rubeus
from website.project.views.file import get_cache_content

from website.addons.osfstorage import model
from website.addons.osfstorage import settings as osf_storage_settings


class OsfStorageNodeLogger(object):

    def __init__(self, node, auth, path=None):
        self.node = node
        self.auth = auth
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"osf_storage_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
        }
        # If logging a file-related action, add the file's view and download URLs
        if self.path:
            params.update({
                'urls': {
                    'view': self.node.web_url_for(
                        'osf_storage_view_file',
                        path=self.path,
                    ),
                    'download': self.node.web_url_for(
                        'osf_storage_download_file',
                        path=self.path,
                    ),
                },
                'path': self.path,
            })
        if extra:
            params.update(extra)
        # Prefix the action with osf_storage_
        self.node.add_log(
            action='osf_storage_{0}'.format(action),
            params=params,
            auth=self.auth,
        )
        if save:
            self.node.save()



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
                'osf_storage_request_signed_url',
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


def get_upload_url(size, content_type, file_path):
    payload = {
        'size': size,
        'type': content_type,
        'path': file_path,
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
        # TODO: Add error handling
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

