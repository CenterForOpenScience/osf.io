from __future__ import unicode_literals

import httplib
import logging

from modularodm.exceptions import NoResultsFound
from modularodm.storage.base import KeyExistsException

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_signed
from framework.transactions.handlers import no_auto_transaction

from website.models import User
from website.project.decorators import (
    must_not_be_registration, must_have_addon,
)
from website.util import rubeus
from website.project.model import has_anonymous_link

from website.models import NodeLog
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


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_download_file_hook(node_addon, payload, **kwargs):
    try:
        path = payload['path'].strip('/')
        version_id = int(payload.get('version', 0)) - 1
    except KeyError:
        raise make_error(httplib.BAD_REQUEST, 'Path is required')
    except ValueError:
        raise make_error(httplib.BAD_REQUEST, 'Version must be an int or not specified')

    storage_node = model.OsfStorageFileNode.get_file(path, node_addon)
    if storage_node.is_deleted:
        raise HTTPError(httplib.GONE)

    version = storage_node.get_version(version_id)

    if payload.get('mode') != 'render':
        if version_id < 0:
            version_id = len(storage_node.versions) + version_id
        utils.update_analytics(node_addon.owner, storage_node._id, version_id)

    return {
        'data': {
            'name': storage_node.name,
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

    if osf_storage_settings.DISK_SAVING_MODE:
        raise HTTPError(httplib.METHOD_NOT_ALLOWED)

    path, user, location, metadata = osf_storage_crud_prepare(node_addon, payload)
    path = path.split('/')

    if len(path) > 2:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        parent, child = path
    except ValueError:
        parent, (child, ) = node_addon.root_node, path

    if not isinstance(parent, model.OsfStorageFileNode):
        parent = model.OsfStorageFileNode.get_folder(parent, node_addon)

    try:
        created, record = False, parent.find_child_by_name(child)
    except NoResultsFound:
        created, record = True, parent.append_file(child)

    code = httplib.CREATED if created else httplib.OK
    version = record.create_version(user, location, metadata)

    return {
        'status': 'success',
        'path': record.path,
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
@utils.handle_odm_errors
@must_not_be_registration
@must_have_addon('osfstorage', 'node')
def osf_storage_crud_hook_delete(payload, node_addon, **kwargs):
    try:
        path = payload['path'].strip('/')
    except KeyError:
        raise make_error(httplib.BAD_REQUEST, 'Path is required')

    storage_node = model.OsfStorageFileNode.get(path, node_addon)

    if storage_node == node_addon.root_node:
        raise HTTPError(httplib.BAD_REQUEST)

    if storage_node.is_deleted:
        raise HTTPError(httplib.GONE)

    try:
        auth = Auth(User.load(payload['auth'].get('id')))
        if not auth:
            raise HTTPError(httplib.BAD_REQUEST)
        storage_node.delete(auth)
    except errors.DeleteError:
        raise HTTPError(httplib.NOT_FOUND)

    storage_node.save()
    return {'status': 'success'}


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_metadata_hook(node_addon, payload, **kwargs):
    path = payload.get('path')

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    if path == '/':
        fileobj = node_addon.root_node
    else:
        fileobj = model.OsfStorageFileNode.get(path.strip('/'), node_addon)

    if not fileobj:
        raise HTTPError(httplib.NOT_FOUND)
    if fileobj.is_deleted:
        raise HTTPError(httplib.GONE)

    if fileobj.kind == 'file':
        data = fileobj.serialized()
        data['fullPath'] = fileobj.materialized_path()
        return data

    return [
        child.serialized()
        for child in fileobj.children
        if not child.is_deleted
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
    is_anon = has_anonymous_link(node, Auth(private_key=payload.get('view_only')))

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    record = model.OsfStorageFileNode.get(path.strip('/'), node_addon)

    # Return revisions in descending order
    return {
        'revisions': [
            utils.serialize_revision(node, record, version, index=len(record.versions) - idx - 1, anon=is_anon)
            for idx, version in enumerate(reversed(record.versions))
        ]
    }


@must_be_signed
@utils.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_create_folder(payload, node_addon, **kwargs):
    path = payload.get('path')
    user = User.from_cookie(payload.get('cookie', ''))

    if not path or not user:
        raise HTTPError(httplib.BAD_REQUEST)

    split = path.strip('/').split('/')
    child = split.pop(-1)

    if not child:
        raise HTTPError(httplib.BAD_REQUEST)

    if split:
        parent = model.OsfStorageFileNode.get(split[0], node_addon)
    else:
        parent = node_addon.root_node

    try:
        folder = parent.append_folder(child)
    except KeyExistsException:
        folder = parent.find_child_by_name(child, kind='folder')
        if not folder.is_deleted:
            raise HTTPError(httplib.CONFLICT, data={
                'message': 'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                    name=folder.name,
                    path=folder.materialized_path(),
                )
            })
        folder.undelete(Auth(user), recurse=False)
    folder.log(Auth(user), NodeLog.FOLDER_CREATED)

    return folder.serialized(), httplib.CREATED
