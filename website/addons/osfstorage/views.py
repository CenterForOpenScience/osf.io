# encoding: utf-8

import os
import httplib
import logging

import requests
from flask import make_response

from framework.auth import Auth
from framework.flask import redirect
from framework.exceptions import HTTPError
from framework.analytics import update_counter
from framework.auth.decorators import must_be_signed
from framework.transactions.handlers import no_auto_transaction

from website.models import User
from website.project.decorators import (
    must_not_be_registration, must_have_addon,
)
from website.util import rubeus

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings as osf_storage_settings


logger = logging.getLogger(__name__)


def make_error(code, message_short=None, message_long=None):
    data = {}
    if message_short:
        data['message_short'] = message_short
    if message_long:
        data['message_long'] = message_long
    return HTTPError(code, data=data)


def get_record_or_404(path, node_addon):
    record = model.OsfStorageFileRecord.find_by_path(path, node_addon)
    if record is not None:
        return record
    raise HTTPError(httplib.NOT_FOUND)


@must_be_signed
@must_have_addon('osfstorage', 'node')
def osf_storage_download_file_hook(node_addon, payload, **kwargs):
    try:
        path = payload['path']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    version_idx, version, record = get_version(path, node_addon, payload.get('version'))

    if payload.get('mode') != 'render':
        update_analytics(node_addon.owner, path, version_idx)

    return {
        'data': {
            'path': version.location_hash,
        },
        'settings': {
            osf_storage_settings.WATERBUTLER_RESOURCE: version.location[osf_storage_settings.WATERBUTLER_RESOURCE],
        },
    }


def osf_storage_crud_prepare(node_addon, payload):
    try:
        auth = payload['auth']
        settings = payload['settings']
        metadata = payload['metadata']
        hashes = payload['hashes']
        worker = payload['worker']
        path = payload['path'].strip('/')
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)
    user = User.load(auth.get('id'))
    if user is None:
        raise HTTPError(httplib.BAD_REQUEST)
    location = settings
    location.update({
        'object': metadata['name'],
        'service': metadata['provider'],
    })
    # TODO: Migrate existing worker host and URL
    location.update(worker)
    metadata.update(hashes)
    return path, user, location, metadata


@must_be_signed
@no_auto_transaction
@must_have_addon('osfstorage', 'node')
def osf_storage_upload_file_hook(node_addon, payload, **kwargs):
    path, user, location, metadata = osf_storage_crud_prepare(node_addon, payload)
    record, created = model.OsfStorageFileRecord.get_or_create(path, node_addon)

    version = record.create_version(user, location, metadata)

    code = httplib.CREATED if created else httplib.OK

    return {
        'status': 'success',
        'version': version._id,
        'downloads': record.get_download_count(),
    }, code


@must_be_signed
@must_have_addon('osfstorage', 'node')
def osf_storage_update_metadata_hook(node_addon, payload, **kwargs):
    try:
        version_id = payload['version']
        metadata = payload['metadata']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    version = model.OsfStorageFileVersion.load(version_id)

    if version is None:
        raise HTTPError(httplib.NOT_FOUND)

    version.update_metadata(metadata)

    return {'status': 'success'}


@must_be_signed
@must_not_be_registration
@must_have_addon('osfstorage', 'node')
def osf_storage_crud_hook_delete(payload, node_addon, **kwargs):
    file_record = model.OsfStorageFileRecord.find_by_path(payload.get('path'), node_addon)

    if file_record is None:
        raise HTTPError(httplib.NOT_FOUND)

    try:
        auth = Auth(User.load(payload['auth'].get('id')))
        if not auth:
            raise HTTPError(httplib.BAD_REQUEST)

        file_record.delete(auth)
    except errors.DeleteError:
        raise HTTPError(httplib.NOT_FOUND)

    file_record.save()
    return {'status': 'success'}


def update_analytics(node, path, version_idx):
    """
    :param Node node: Root node to update
    :param str path: Path to file
    :param int version_idx: One-based version index
    """
    update_counter(u'download:{0}:{1}'.format(node._id, path))
    update_counter(u'download:{0}:{1}:{2}'.format(node._id, path, version_idx))


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_metadata_hook(node_addon, payload, **kwargs):
    path = payload['path']

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    if path == '/':
        fileobj = node_addon.root_node
    else:
        fileobj = model.OsfStorageNode.get(path.strip('/'), node_addon)

    if fileobj.is_deleted:
        raise HTTPError(httplib.GONE)

    if fileobj.kind == 'file':
        return utils.serialize_metadata(fileobj)

    return [
        utils.serialize_metadata(child)
        for child in fileobj.children
    ]


def osf_storage_root(node_settings, auth, **kwargs):
    """Build HGrid JSON for root node. Note: include node URLs for client-side
    URL creation for uploaded files.
    """
    node = node_settings.owner
    root = rubeus.build_addon_root(
        node_settings=node_settings,
        name='',
        permissions=auth,
        user=auth.user,
        nodeUrl=node.url,
        nodeApiUrl=node.api_url,
    )
    return [root]


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_revisions(payload, node_addon, **kwargs):
    node = node_addon.owner
    path = payload.get('path')

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    record = model.OsfStorageNode.get(path.strip('/'), node_addon)

    return {
        'revisions': [
            utils.serialize_revision(node, record, version, idx)
            for idx, version in enumerate(record.versions)
        ]
    }


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_create_folder(payload, node_addon, **kwargs):
    path = payload.get('path')
    split = path.strip('/').split('/')
    child = split.pop(-1)

    if not child:
        raise HTTPError(httplib.BAD_REQUEST)

    if split:
        parent = model.OsfStorageNode.get(split[0], node_addon)
    else:
        parent = node_addon.root_node

    return utils.serialize_metadata(parent.append_folder(child)), httplib.CREATED
