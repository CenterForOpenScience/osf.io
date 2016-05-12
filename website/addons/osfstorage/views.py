from __future__ import unicode_literals

import httplib
import logging

from modularodm import Q
from modularodm.storage.base import KeyExistsException

from flask import request

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_signed

from website.exceptions import InvalidTagError, TagNotFoundError
from website.models import User
from website.project.decorators import (
    must_not_be_registration, must_have_addon, must_have_permission
)
from website.util import rubeus
from website.project.model import has_anonymous_link

from website.files import models
from website.files import exceptions
from website.addons.osfstorage import utils
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
def osfstorage_update_metadata(node_addon, payload, **kwargs):
    try:
        version_id = payload['version']
        metadata = payload['metadata']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    version = models.FileVersion.load(version_id)

    if version is None:
        raise HTTPError(httplib.NOT_FOUND)

    version.update_metadata(metadata)

    return {'status': 'success'}

@must_be_signed
@decorators.autoload_filenode(must_be='file')
def osfstorage_get_revisions(file_node, node_addon, payload, **kwargs):
    is_anon = has_anonymous_link(node_addon.owner, Auth(private_key=request.args.get('view_only')))

    # Return revisions in descending order
    return {
        'revisions': [
            utils.serialize_revision(node_addon.owner, file_node, version, index=len(file_node.versions) - idx - 1, anon=is_anon)
            for idx, version in enumerate(reversed(file_node.versions))
        ]
    }


@decorators.waterbutler_opt_hook
def osfstorage_copy_hook(source, destination, name=None, **kwargs):
    return source.copy_under(destination, name=name).serialize(), httplib.CREATED


@decorators.waterbutler_opt_hook
def osfstorage_move_hook(source, destination, name=None, **kwargs):
    try:
        return source.move_under(destination, name=name).serialize(), httplib.OK
    except exceptions.FileNodeCheckedOutError:
        raise HTTPError(httplib.METHOD_NOT_ALLOWED, data={
            'message_long': 'Cannot move file as it is checked out.'
        })

@must_be_signed
@decorators.autoload_filenode(default_root=True)
def osfstorage_get_lineage(file_node, node_addon, **kwargs):
    #TODO Profile
    list(models.OsfStorageFolder.find(Q('node', 'eq', node_addon.owner)))

    lineage = []

    while file_node:
        lineage.append(file_node.serialize())
        file_node = file_node.parent

    return {'data': lineage}


@must_be_signed
@decorators.autoload_filenode(default_root=True)
def osfstorage_get_metadata(file_node, **kwargs):
    try:
        # TODO This should change to version as its internal it can be changed anytime
        version = int(request.args.get('revision'))
    except (ValueError, TypeError):  # If its not a number
        version = None
    return file_node.serialize(version=version, include_full=True)


@must_be_signed
@decorators.autoload_filenode(must_be='folder')
def osfstorage_get_children(file_node, **kwargs):
    return [
        child.serialize()
        for child in file_node.children
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
        created, file_node = False, parent.find_child_by_name(name, kind=int(not is_folder))

    if not created and is_folder:
        raise HTTPError(httplib.CONFLICT, data={
            'message': 'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                name=file_node.name,
                path=file_node.materialized_path,
            )
        })

    if not is_folder:
        try:
            if file_node.checkout is None or file_node.checkout._id == user._id:
                version = file_node.create_version(
                    user,
                    dict(payload['settings'], **dict(
                        payload['worker'], **{
                            'object': payload['metadata']['name'],
                            'service': payload['metadata']['provider'],
                        })
                    ),
                    dict(payload['metadata'], **payload['hashes'])
                )
                version_id = version._id
                archive_exists = version.archive is not None
            else:
                raise HTTPError(httplib.FORBIDDEN, data={
                    'message_long': 'File cannot be updated due to checkout status.'
                })
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)
    else:
        version_id = None
        archive_exists = False

    return {
        'status': 'success',
        'archive': not archive_exists,  # Should waterbutler also archive this file
        'data': file_node.serialize(),
        'version': version_id,
    }, httplib.CREATED if created else httplib.OK


@must_be_signed
@must_not_be_registration
@decorators.autoload_filenode()
def osfstorage_delete(file_node, payload, node_addon, **kwargs):
    auth = Auth(User.load(payload['user']))

    #TODO Auth check?
    if not auth:
        raise HTTPError(httplib.BAD_REQUEST)

    if file_node == node_addon.get_root():
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        file_node.delete()

    except exceptions.FileNodeCheckedOutError:
        raise HTTPError(httplib.FORBIDDEN)

    return {'status': 'success'}


@must_be_signed
@decorators.autoload_filenode(must_be='file')
def osfstorage_download(file_node, payload, node_addon, **kwargs):
    if not request.args.get('version'):
        version_id = None
    else:
        try:
            version_id = int(request.args['version'])
        except ValueError:
            raise make_error(httplib.BAD_REQUEST, message_short='Version must be an integer if not specified')

    version = file_node.get_version(version_id, required=True)

    if request.args.get('mode') not in ('render', ):
        utils.update_analytics(node_addon.owner, file_node._id, int(version.identifier) - 1)

    return {
        'data': {
            'name': file_node.name,
            'path': version.location_hash,
        },
        'settings': {
            osf_storage_settings.WATERBUTLER_RESOURCE: version.location[osf_storage_settings.WATERBUTLER_RESOURCE],
        },
    }


@must_have_permission('write')
@decorators.autoload_filenode(must_be='file')
def osfstorage_add_tag(file_node, **kwargs):
    data = request.get_json()
    if file_node.add_tag(data['tag'], kwargs['auth']):
        return {'status': 'success'}, httplib.OK
    return {'status': 'failure'}, httplib.BAD_REQUEST

@must_have_permission('write')
@decorators.autoload_filenode(must_be='file')
def osfstorage_remove_tag(file_node, **kwargs):
    data = request.get_json()
    try:
        file_node.remove_tag(data['tag'], kwargs['auth'])
    except TagNotFoundError:
        return {'status': 'failure'}, httplib.CONFLICT
    except InvalidTagError:
        return {'status': 'failure'}, httplib.BAD_REQUEST
    else:
        return {'status': 'success'}, httplib.OK
