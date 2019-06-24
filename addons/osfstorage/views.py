from __future__ import unicode_literals

import httplib
import logging

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import connection
from django.db import transaction

from flask import request

from framework.auth import Auth
from framework.sessions import get_session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_signed, must_be_logged_in

from api.caching.tasks import update_storage_usage
from osf.exceptions import InvalidTagError, TagNotFoundError
from osf.models import FileVersion, OSFUser
from osf.utils.permissions import WRITE
from osf.utils.requests import check_select_for_update
from website.project.decorators import (
    must_not_be_registration, must_have_permission
)
from website.project.model import has_anonymous_link

from website.files import exceptions
from addons.osfstorage import utils
from addons.osfstorage import decorators
from addons.osfstorage.models import OsfStorageFolder
from addons.osfstorage import settings as osf_storage_settings


logger = logging.getLogger(__name__)


def make_error(code, message_short=None, message_long=None):
    data = {}
    if message_short:
        data['message_short'] = message_short
    if message_long:
        data['message_long'] = message_long
    return HTTPError(code, data=data)


@must_be_signed
def osfstorage_update_metadata(payload, **kwargs):
    """Metadata received from WaterButler, is built incrementally via latent task calls to this endpoint.

    The basic metadata response looks like::

        {
            "metadata": {
                # file upload
                "name": "file.name",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "path": "...",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "version": "2",
                "downloads": "1",
                "checkout": "...",
                "latestVersionSeen": {"userId": "abc12", "seen": true},
                "modified": "a date",
                "modified_utc": "a date in utc",

                # glacier vault (optional)
                "archive": "glacier_key",
                "vault": "glacier_vault_name",

                # parity files
                "parity": {
                    "redundancy": "5",
                    "files": [
                        {"name": "foo.txt.par2","sha256": "abc123"},
                        {"name": "foo.txt.vol00+01.par2","sha256": "xyz321"},
                    ]
                }
            },
        }
    """
    try:
        version_id = payload['version']
        metadata = payload['metadata']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if check_select_for_update():
        version = FileVersion.objects.filter(_id=version_id).select_for_update().first()
    else:
        version = FileVersion.objects.filter(_id=version_id).first()

    if version is None:
        raise HTTPError(httplib.NOT_FOUND)

    version.update_metadata(metadata)

    return {'status': 'success'}

@must_be_signed
@decorators.autoload_filenode(must_be='file')
def osfstorage_get_revisions(file_node, payload, target, **kwargs):
    from osf.models import PageCounter, FileVersion  # TODO Fix me onces django works
    is_anon = has_anonymous_link(target, Auth(private_key=request.args.get('view_only')))

    counter_prefix = 'download:{}:{}:'.format(file_node.target._id, file_node._id)

    version_count = file_node.versions.count()
    # Don't worry. The only % at the end of the LIKE clause, the index is still used
    counts = dict(PageCounter.objects.filter(_id__startswith=counter_prefix).values_list('_id', 'total'))
    qs = FileVersion.includable_objects.filter(basefilenode__id=file_node.id).include('creator__guids').order_by('-created')

    for i, version in enumerate(qs):
        version._download_count = counts.get('{}{}'.format(counter_prefix, version_count - i - 1), 0)

    # Return revisions in descending order
    return {
        'revisions': [
            utils.serialize_revision(target, file_node, version, index=version_count - idx - 1, anon=is_anon)
            for idx, version in enumerate(qs)
        ]
    }


@decorators.waterbutler_opt_hook
def osfstorage_copy_hook(source, destination, name=None, **kwargs):
    ret = source.copy_under(destination, name=name).serialize(), httplib.CREATED
    update_storage_usage(destination.target)
    return ret

@decorators.waterbutler_opt_hook
def osfstorage_move_hook(source, destination, name=None, **kwargs):
    source_target = source.target

    try:
        ret = source.move_under(destination, name=name).serialize(), httplib.OK
    except exceptions.FileNodeCheckedOutError:
        raise HTTPError(httplib.METHOD_NOT_ALLOWED, data={
            'message_long': 'Cannot move file as it is checked out.'
        })
    except exceptions.FileNodeIsPrimaryFile:
        raise HTTPError(httplib.FORBIDDEN, data={
            'message_long': 'Cannot move file as it is the primary file of preprint.'
        })

    # once the move is complete recalculate storage for both targets if it's a inter-target move.
    if source_target != destination.target:
        update_storage_usage(destination.target)
        update_storage_usage(source_target)

    return ret

@must_be_signed
@decorators.autoload_filenode(default_root=True)
def osfstorage_get_lineage(file_node, **kwargs):
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
    from django.contrib.contenttypes.models import ContentType
    user_id = request.args.get('user_id')
    user_content_type_id = ContentType.objects.get_for_model(OSFUser).id
    user_pk = OSFUser.objects.filter(guids___id=user_id, guids___id__isnull=False).values_list('pk', flat=True).first()
    with connection.cursor() as cursor:
        # Read the documentation on FileVersion's fields before reading this code
        cursor.execute("""
            SELECT json_agg(CASE
                WHEN F.type = 'osf.osfstoragefile' THEN
                    json_build_object(
                        'id', F._id
                        , 'path', '/' || F._id
                        , 'name', F.name
                        , 'kind', 'file'
                        , 'size', LATEST_VERSION.size
                        , 'downloads',  COALESCE(DOWNLOAD_COUNT, 0)
                        , 'version', (SELECT COUNT(*) FROM osf_basefileversionsthrough WHERE osf_basefileversionsthrough.basefilenode_id = F.id)
                        , 'contentType', LATEST_VERSION.content_type
                        , 'modified', LATEST_VERSION.created
                        , 'created', EARLIEST_VERSION.created
                        , 'checkout', CHECKOUT_GUID
                        , 'md5', LATEST_VERSION.metadata ->> 'md5'
                        , 'sha256', LATEST_VERSION.metadata ->> 'sha256'
                        , 'latestVersionSeen', SEEN_LATEST_VERSION.case
                    )
                ELSE
                    json_build_object(
                        'id', F._id
                        , 'path', '/' || F._id || '/'
                        , 'name', F.name
                        , 'kind', 'folder'
                    )
                END
            )
            FROM osf_basefilenode AS F
            LEFT JOIN LATERAL (
                SELECT * FROM osf_fileversion
                JOIN osf_basefileversionsthrough ON osf_fileversion.id = osf_basefileversionsthrough.fileversion_id
                WHERE osf_basefileversionsthrough.basefilenode_id = F.id
                ORDER BY created DESC
                LIMIT 1
            ) LATEST_VERSION ON TRUE
            LEFT JOIN LATERAL (
                SELECT * FROM osf_fileversion
                JOIN osf_basefileversionsthrough ON osf_fileversion.id = osf_basefileversionsthrough.fileversion_id
                WHERE osf_basefileversionsthrough.basefilenode_id = F.id
                ORDER BY created ASC
                LIMIT 1
            ) EARLIEST_VERSION ON TRUE
            LEFT JOIN LATERAL (
                SELECT _id from osf_guid
                WHERE object_id = F.checkout_id
                AND content_type_id = %s
                LIMIT 1
            ) CHECKOUT_GUID ON TRUE
            LEFT JOIN LATERAL (
                SELECT P.total AS DOWNLOAD_COUNT FROM osf_pagecounter AS P
                WHERE P._id = 'download:' || %s || ':' || F._id
                LIMIT 1
            ) DOWNLOAD_COUNT ON TRUE
            LEFT JOIN LATERAL (
              SELECT EXISTS(
                SELECT (1) FROM osf_fileversionusermetadata
                  INNER JOIN osf_fileversion ON osf_fileversionusermetadata.file_version_id = osf_fileversion.id
                  INNER JOIN osf_basefileversionsthrough ON osf_fileversion.id = osf_basefileversionsthrough.fileversion_id
                  WHERE osf_fileversionusermetadata.user_id = %s
                  AND osf_basefileversionsthrough.basefilenode_id = F.id
                LIMIT 1
              )
            ) SEEN_FILE ON TRUE
            LEFT JOIN LATERAL (
                SELECT CASE WHEN SEEN_FILE.exists
                THEN
                    CASE WHEN EXISTS(
                      SELECT (1) FROM osf_fileversionusermetadata
                      WHERE osf_fileversionusermetadata.file_version_id = LATEST_VERSION.fileversion_id
                      AND osf_fileversionusermetadata.user_id = %s
                      LIMIT 1
                    )
                    THEN
                      json_build_object('user', %s, 'seen', TRUE)
                    ELSE
                      json_build_object('user', %s, 'seen', FALSE)
                    END
                ELSE
                  NULL
                END
            ) SEEN_LATEST_VERSION ON TRUE
            WHERE parent_id = %s
            AND (NOT F.type IN ('osf.trashedfilenode', 'osf.trashedfile', 'osf.trashedfolder'))
        """, [
            user_content_type_id,
            file_node.target._id,
            user_pk,
            user_pk,
            user_id,
            user_id,
            file_node.id
        ])
        return cursor.fetchone()[0] or []


@must_be_signed
@decorators.autoload_filenode(must_be='folder')
def osfstorage_create_child(file_node, payload, **kwargs):
    parent = file_node  # Just for clarity
    name = payload.get('name')
    user = OSFUser.load(payload.get('user'))
    is_folder = payload.get('kind') == 'folder'

    if getattr(file_node.target, 'is_registration', False) and not getattr(file_node.target, 'archiving', False):
        raise HTTPError(
            httplib.BAD_REQUEST,
            data={
                'message_short': 'Registered Nodes are immutable',
                'message_long': "The operation you're trying to do cannot be applied to registered Nodes, which are immutable",
            }
        )

    if not (name or user) or '/' in name:
        raise HTTPError(httplib.BAD_REQUEST)

    if getattr(file_node.target, 'is_quickfiles', False) and is_folder:
        raise HTTPError(httplib.BAD_REQUEST, data={'message_long': 'You may not create a folder for QuickFiles'})

    try:
        # Create a save point so that we can rollback and unlock
        # the parent record
        with transaction.atomic():
            if is_folder:
                created, file_node = True, parent.append_folder(name)
            else:
                created, file_node = True, parent.append_file(name)
    except (ValidationError, IntegrityError):
        created, file_node = False, parent.find_child_by_name(name, kind=int(not is_folder))

    if not created and is_folder:
        raise HTTPError(httplib.CONFLICT, data={
            'message_long': 'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                name=file_node.name,
                path=file_node.materialized_path,
            )
        })

    if file_node.checkout and file_node.checkout._id != user._id:
        raise HTTPError(httplib.FORBIDDEN, data={
            'message_long': 'File cannot be updated due to checkout status.'
        })

    if not is_folder:
        try:
            metadata = dict(payload['metadata'], **payload['hashes'])
            location = dict(payload['settings'], **dict(
                payload['worker'], **{
                    'object': payload['metadata']['name'],
                    'service': payload['metadata']['provider'],
                }
            ))
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)

        current_version = file_node.get_version()
        new_version = file_node.create_version(user, location, metadata)

        if not current_version or not current_version.is_duplicate(new_version):
            update_storage_usage(file_node.target)

        version_id = new_version._id
        archive_exists = new_version.archive is not None
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
def osfstorage_delete(file_node, payload, target, **kwargs):
    user = OSFUser.load(payload['user'])
    auth = Auth(user)

    #TODO Auth check?
    if not auth:
        raise HTTPError(httplib.BAD_REQUEST)
    if file_node == OsfStorageFolder.objects.get_root(target=target):
            raise HTTPError(httplib.BAD_REQUEST)

    try:
        file_node.delete(user=user)

    except exceptions.FileNodeCheckedOutError:
        raise HTTPError(httplib.FORBIDDEN)
    except exceptions.FileNodeIsPrimaryFile:
        raise HTTPError(httplib.FORBIDDEN, data={
            'message_long': 'Cannot delete file as it is the primary file of preprint.'
        })

    update_storage_usage(file_node.target)
    return {'status': 'success'}


@must_be_signed
@decorators.autoload_filenode(must_be='file')
def osfstorage_download(file_node, payload, **kwargs):
    # Set user ID in session data for checking if user is contributor
    # to project.
    user_id = payload.get('user')
    if user_id:
        current_session = get_session()
        current_session.data['auth_user_id'] = user_id
        current_session.save()

    if not request.args.get('version'):
        version_id = None
    else:
        try:
            version_id = int(request.args['version'])
        except ValueError:
            raise make_error(httplib.BAD_REQUEST, message_short='Version must be an integer if not specified')

    version = file_node.get_version(version_id, required=True)
    file_version_thru = version.get_basefilenode_version(file_node)
    name = file_version_thru.version_name if file_version_thru else file_node.name

    return {
        'data': {
            'name': name,
            'path': version.location_hash,
        },
        'settings': {
            osf_storage_settings.WATERBUTLER_RESOURCE: version.location[osf_storage_settings.WATERBUTLER_RESOURCE],
        },
    }


@must_have_permission(WRITE)
@decorators.autoload_filenode(must_be='file')
def osfstorage_add_tag(file_node, **kwargs):
    data = request.get_json()
    if file_node.add_tag(data['tag'], kwargs['auth']):
        return {'status': 'success'}, httplib.OK
    return {'status': 'failure'}, httplib.BAD_REQUEST

@must_have_permission(WRITE)
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


@must_be_logged_in
def update_region(auth, **kwargs):
    user = auth.user
    user_settings = user.get_addon('osfstorage')

    data = request.get_json()
    try:
        region_id = data['region_id']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    try:
        user_settings.set_region(region_id)
    except ValueError:
        raise HTTPError(404, data=dict(message_short='Region not found',
                                    message_long='A storage region with this id does not exist'))
    return {'message': 'User region updated.'}
