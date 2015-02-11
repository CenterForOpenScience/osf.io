# encoding: utf-8

import os
import httplib
import logging

import requests
from flask import request, make_response

from framework.auth import Auth
from framework.flask import redirect
from framework.exceptions import HTTPError
from framework.analytics import update_counter
from framework.auth.decorators import must_be_signed
from framework.transactions.handlers import no_auto_transaction

from website.models import User
from website.project.decorators import (
    must_be_contributor_or_public,
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


def parse_version_specifier(version_str):
    """
    :raise: `InvalidVersionError` if version specifier cannot be parsed
    """
    try:
        version_idx = int(version_str)
    except (TypeError, ValueError):
        raise errors.InvalidVersionError
    if version_idx < 1:
        raise errors.InvalidVersionError
    return version_idx


def get_version_helper(file_record, version_str):
    """
    :return: Tuple of (version_index, file_version); note that index is one-based
    :raise: `HTTPError` if version specifier is invalid or version not found
    """
    if version_str is None:
        return (
            len(file_record.versions),
            file_record.versions[-1],
        )
    try:
        version_idx = parse_version_specifier(version_str)
    except errors.InvalidVersionError:
        raise make_error(httplib.BAD_REQUEST, 'Invalid version')
    try:
        return version_idx, file_record.versions[version_idx - 1]
    except IndexError:
        raise HTTPError(httplib.NOT_FOUND)


def get_version(path, node_settings, version_str, throw=True):
    """Resolve version from request arguments.

    :param str path: Path to file
    :param node_settings: Node settings record
    :param str version_str: Version from query string
    :param bool throw: Throw `HTTPError` if version is incomplete
    :return: Tuple of (<one-based version index>, <file version>, <file record>)
    """
    record = model.OsfStorageFileRecord.find_by_path(path, node_settings)

    if record is None:
        raise HTTPError(httplib.NOT_FOUND)

    if record.is_deleted:
        raise HTTPError(httplib.GONE)

    version_idx, file_version = get_version_helper(record, version_str)
    return version_idx, file_version, record


def download_file(path, node_addon, version_query, **query):
    idx, version, record = get_version(path, node_addon, version_query)
    url = utils.get_waterbutler_download_url(idx, version, record, **query)
    # Redirect the user directly to the backend service (CloudFiles or S3) rather than
    # routing through OSF; this saves a request and avoids potential CORS configuration
    # errors in WaterButler.
    resp = requests.get(url, allow_redirects=False)
    if resp.status_code in [301, 302]:
        return redirect(resp.headers['Location'])
    else:
        response = make_response(resp.content)
        filename = record.name.encode('utf-8')
        if version != record.versions[-1]:
            # add revision to filename
            # foo.mp3 -> foo-abc123.mp3
            filename = '-{}'.format(version.date_created.strftime('%Y-%m-%d')).join(os.path.splitext(filename))
        disposition = 'attachment; filename={}'.format(filename)
        response.headers['Content-Disposition'] = disposition
        response.headers['Content-Type'] = 'application/octet-stream'
        return response


@must_be_contributor_or_public
@must_have_addon('osfstorage', 'node')
def osf_storage_view_file(auth, path, node_addon, **kwargs):
    action = request.args.get('action', 'view')
    version_idx = request.args.get('version')
    if action == 'download':
        mode = request.args.get('mode')
        return download_file(path, node_addon, version_idx, mode=mode)
    # if action == 'view':
    #     return view_file(auth, path, node_addon, version_idx)
    raise HTTPError(httplib.BAD_REQUEST)


def update_analytics(node, path, version_idx):
    """
    :param Node node: Root node to update
    :param str path: Path to file
    :param int version_idx: One-based version index
    """
    update_counter(u'download:{0}:{1}'.format(node._id, path))
    update_counter(u'download:{0}:{1}:{2}'.format(node._id, path, version_idx))


@must_be_signed
@must_have_addon('osfstorage', 'node')
def osf_storage_get_metadata_hook(node_addon, payload, **kwargs):
    node = node_addon.owner
    path = payload.get('path', '')

    if path.endswith('/') or not path:
        file_tree = model.OsfStorageFileTree.find_by_path(path, node_addon)
        if file_tree is None:
            if path == '':
                return []
            raise HTTPError(httplib.NOT_FOUND)
        # TODO: Handle nested folders
        return [
            utils.serialize_metadata_hgrid(item, node)
            for item in list(file_tree.children)
            if not item.is_deleted
        ]
    else:
        file_record = model.OsfStorageFileRecord.find_by_path(path, node_addon)
        if not file_record:
            raise HTTPError(httplib.NOT_FOUND)

        if file_record.is_deleted:
            raise HTTPError(httplib.GONE)

        return utils.serialize_metadata_hgrid(file_record, node)


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
@must_have_addon('osfstorage', 'node')
def osf_storage_get_revisions(payload, node_addon, **kwargs):
    node = node_addon.owner
    page = payload.get('page') or 0
    path = payload.get('path')

    if not path:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        page = int(page)
    except (TypeError, ValueError):
        raise HTTPError(httplib.BAD_REQUEST)

    record = model.OsfStorageFileRecord.find_by_path(path, node_addon)

    if record is None:
        raise HTTPError(httplib.NOT_FOUND)

    indices, versions, more = record.get_versions(
        page,
        size=osf_storage_settings.REVISIONS_PAGE_SIZE,
    )

    return {
        'revisions': [
            utils.serialize_revision(node, record, versions[idx], indices[idx])
            for idx in range(len(versions))
        ],
        'more': more,
    }
