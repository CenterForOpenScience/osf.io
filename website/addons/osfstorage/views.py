from __future__ import unicode_literals

import httplib
import logging

from modularodm import Q
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

from website.models import Node
from website.models import NodeLog
from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import errors
from website.addons.osfstorage import decorators
from website.addons.osfstorage import settings as osf_storage_settings


logger = logging.getLogger(__name__)


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


def make_error(code, message_short=None, message_long=None):
    data = {}
    if message_short:
        data['message_short'] = message_short
    if message_long:
        data['message_long'] = message_long
    return HTTPError(code, data=data)


@must_be_signed
@must_have_addon('osfstorage', 'node')
def osf_storage_update_metadata(node_addon, payload, **kwargs):
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
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_revisions(payload, node_addon, **kwargs):
    node = node_addon.owner
    path = payload.get('path')
    is_anon = has_anonymous_link(node, Auth(private_key=payload.get('view_only')))

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    record = model.OsfStorageFileNode.get(path.strip('/'), node_addon)

    return {
        'revisions': list(reversed([
            utils.serialize_revision(node, record, version, idx, anon=is_anon)
            for idx, version in enumerate(reversed(record.versions))
        ]))
    }


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_create_folder(payload, node_addon, **kwargs):
    path = payload.get('path')
    user = User.load(payload.get('user'))

    if not path or not user:
        raise HTTPError(httplib.BAD_REQUEST)

    created, folder = model.OsfStorageFileNode.create_child_by_path(path, node_addon)

    if not created:
        if folder.is_deleted:
            folder.undelete(Auth(user), recurse=False)
        else:
            raise HTTPError(httplib.CONFLICT, data={
                'message': 'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                    name=folder.name,
                    path=folder.materialized_path(),
                )
            })

    folder.log(Auth(user), NodeLog.FOLDER_CREATED)
    return folder.serialized(), httplib.CREATED


@decorators.waterbutler_opt_hook
def osf_storage_copy_hook(source, destination, name=None, **kwargs):
    return source.copy_under(destination, name=name).serialized(), httplib.CREATED


@decorators.waterbutler_opt_hook
def osf_storage_move_hook(source, destination, name=None, **kwargs):
    return source.move_under(destination, name=name).serialized(), httplib.OK


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_lineage(node_addon, fid=None, **kwargs):
    filenode = model.OsfStorageFileNode.get(fid or node_addon.root_node._id, node_addon)

    #TODO Profile
    list(model.OsfStorageFileNode.find(Q('kind', 'eq', 'folder') & Q('node_settings', 'eq', node_addon)))

    lineage = []

    while filenode:
        lineage.append(filenode.serialized())
        filenode = filenode.parent

    return {'data': lineage}


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_metadata(node_addon, fid=None, **kwargs):
    filenode = model.OsfStorageFileNode.get(
        fid or node_addon.root_node._id,
        node_addon=node_addon
    )

    if filenode.is_deleted:
        raise HTTPError(httplib.GONE)

    return filenode.serialized(include_full=True)


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_get_children(node_addon, fid, **kwargs):
    filenode = model.OsfStorageFileNode.get(fid, node_addon)

    if filenode.is_deleted:
        raise HTTPError(httplib.GONE)

    if filenode.is_file:
        raise HTTPError(httplib.BAD_REQUEST)

    return [
        child.serialized()
        for child in filenode.children
        if not child.is_deleted
    ]


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_create_child(fid, payload, node_addon, **kwargs):
    name = payload['name']
    user = User.load(payload['user'])
    is_folder = payload.get('kind') == 'folder'
    parent = model.OsfStorageFileNode.get_folder(fid, node_addon)

    try:
        if is_folder:
            created, file_node = True, parent.append_folder(name)
        else:
            created, file_node = True, parent.append_file(name)
    except KeyExistsException:
        file_node = parent.find_child_by_name(name, kind='folder' if is_folder else 'file')
        created = False

    # if not created and is_folder:
    if file_node.is_deleted:
        file_node.undelete(Auth(user), recurse=False)
    else:
        if not created and is_folder:
            raise HTTPError(httplib.CONFLICT, data={
                'message': 'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                    name=file_node.name,
                    path=file_node.materialized_path(),
                )
            })

    if is_folder:
        #TODO Handle copies
        file_node.log(Auth(user), NodeLog.FOLDER_CREATED)
    else:
        try:
            file_node.create_version(
                user,
                dict(payload['settings'], **dict(
                    payload['worker'], **{
                        'object': payload['metadata']['name'],
                        'service': payload['metadata']['provider'],
                    })
                ),
                dict(payload['metadata'], **payload['hashes'])
            )
        except KeyError:
            #TODO Handle redeleting
            raise HTTPError(httplib.BAD_REQUEST)
        file_node.log(Auth(user), NodeLog.FILE_ADDED)

    return file_node.serialized(), httplib.CREATED if created else httplib.OK


@must_be_signed
@decorators.handle_odm_errors
@must_not_be_registration
@must_have_addon('osfstorage', 'node')
def osf_storage_delete(fid, payload, node_addon, **kwargs):
    auth = Auth(User.load(payload['user']))
    file_node = model.OsfStorageFileNode.get(fid, node_addon)

    if not auth:
        raise HTTPError(httplib.BAD_REQUEST)

    if file_node == node_addon.root_node:
        raise HTTPError(httplib.BAD_REQUEST)

    if file_node.is_deleted:
        raise HTTPError(httplib.GONE)

    try:
        file_node.delete(auth)
    except errors.DeleteError:
        raise HTTPError(httplib.NOT_FOUND)

    file_node.save()
    return {'status': 'success'}


@must_be_signed
@decorators.handle_odm_errors
@must_have_addon('osfstorage', 'node')
def osf_storage_download(fid, payload, node_addon, **kwargs):
    try:
        version_id = int(payload.get('version', 0)) - 1
    except ValueError:
        raise make_error(httplib.BAD_REQUEST, 'Version must be an int or not specified')

    file_node = model.OsfStorageFileNode.get_file(fid, node_addon)

    if file_node.is_deleted:
        raise HTTPError(httplib.GONE)

    version = file_node.get_version(version_id)

    if payload.get('mode') not in ('render', ):
        if version_id < 0:
            version_id = len(file_node.versions) + version_id
        utils.update_analytics(node_addon.owner, file_node._id, version_id)

    return {
        'data': {
            'name': file_node.name,
            'path': version.location_hash,
        },
        'settings': {
            osf_storage_settings.WATERBUTLER_RESOURCE: version.location[osf_storage_settings.WATERBUTLER_RESOURCE],
        },
    }
