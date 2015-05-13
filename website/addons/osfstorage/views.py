from __future__ import unicode_literals

import httplib
import logging

from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_signed

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
def osfstorage_update_metadata(node_addon, payload, **kwargs):
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
@decorators.autoload_filenode(must_be='file')
def osfstorage_get_revisions(file_node, node_addon, payload, **kwargs):
    is_anon = has_anonymous_link(node_addon.owner, Auth(private_key=payload.get('view_only')))

    # Return revisions in descending order
    return {
        'revisions': [
            utils.serialize_revision(node_addon.owner, file_node, version, index=len(file_node.versions) - idx - 1, anon=is_anon)
            for idx, version in enumerate(reversed(file_node.versions))
        ]
    }


@decorators.waterbutler_opt_hook
def osfstorage_copy_hook(source, destination, name=None, **kwargs):
    return source.copy_under(destination, name=name).serialized(), httplib.CREATED


@decorators.waterbutler_opt_hook
def osfstorage_move_hook(source, destination, name=None, **kwargs):
    return source.move_under(destination, name=name).serialized(), httplib.OK


@must_be_signed
@decorators.autoload_filenode(default_root=True)
def osfstorage_get_lineage(file_node, node_addon, **kwargs):
    #TODO Profile
    list(model.OsfStorageFileNode.find(Q('kind', 'eq', 'folder') & Q('node_settings', 'eq', node_addon)))

    lineage = []

    while file_node:
        lineage.append(file_node.serialized())
        file_node = file_node.parent

    return {'data': lineage}


@must_be_signed
@decorators.autoload_filenode(default_root=True)
def osfstorage_get_metadata(file_node, **kwargs):
    if file_node.is_deleted:
        raise HTTPError(httplib.GONE)

    return file_node.serialized(include_full=True)


@must_be_signed
@decorators.autoload_filenode(must_be='folder')
def osfstorage_get_children(file_node, **kwargs):
    if file_node.is_deleted:
        raise HTTPError(httplib.GONE)

    return [
        child.serialized()
        for child in file_node.children
        if not child.is_deleted
    ]


@must_be_signed
@must_not_be_registration
@decorators.autoload_filenode(must_be='folder')
def osfstorage_create_child(file_node, payload, node_addon, **kwargs):
    parent = file_node  # Just for clarity
    name = payload.get('name')
    user = User.load(payload.get('user'))
    is_folder = payload.get('kind') == 'folder'

    if not (name or user) or '/' in name:
        raise HTTPError(httplib.BAD_REQUEST)

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

    return {
        'status': 'success',
        'data': file_node.serialized(),
        'version': None if is_folder else file_node.versions[-1]._id
    }, httplib.CREATED if created else httplib.OK


@must_be_signed
@must_not_be_registration
@decorators.autoload_filenode()
def osfstorage_delete(file_node, payload, node_addon, **kwargs):
    auth = Auth(User.load(payload['user']))

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
@decorators.autoload_filenode(must_be='file')
def osfstorage_download(file_node, payload, node_addon, **kwargs):
    if file_node.is_deleted:
        raise HTTPError(httplib.GONE)

    try:
        version_id = int(payload.get('version', 0)) - 1
    except ValueError:
        raise make_error(httplib.BAD_REQUEST, 'Version must be an int or not specified')

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


# lol
for key, item in locals().items():
    if callable(item) and key.startswith('osfstorage'):
        locals()[key] = must_have_addon('osfstorage', 'node')(item)
