# -*- coding: utf-8 -*-

import os
import cgi
import time
import hashlib
from cStringIO import StringIO
import httplib as http
import logging

from flask import request, send_file
from modularodm import Q

from framework.flask import redirect
from framework.exceptions import HTTPError
from framework.analytics import get_basic_counters, update_counters
from framework.auth.utils import privacy_info_handle
from website.project.views.node import _view_project
from website.project.decorators import (
    must_not_be_registration, must_be_valid_project,
    must_be_contributor_or_public, must_have_addon, must_have_permission
)
from website.project.views.file import get_cache_content, prepare_file
from website.project.model import has_anonymous_link
from website.addons.base.views import check_file_guid
from website import settings
from website.project.model import NodeLog
from website.util import rubeus, permissions

from website.addons.osffiles.model import NodeFile, OsfGuidFile
from website.addons.osffiles.exceptions import FileNotModified
from website.addons.osffiles.utils import get_latest_version_number, urlsafe_filename
from website.addons.osffiles.exceptions import (
    InvalidVersionError,
    VersionNotFoundError,
    FileNotFoundError,
)

logger = logging.getLogger(__name__)


def _clean_file_name(name):
    " HTML-escape file name and encode to UTF-8. "
    escaped = cgi.escape(name)
    encoded = unicode(escaped).encode('utf-8')
    return encoded


def get_osffiles_hgrid(node_settings, auth, **kwargs):

    node = node_settings.owner

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    info = []

    if can_view:

        for name, fid in node.files_current.iteritems():

            fobj = NodeFile.load(fid)
            item = {
                rubeus.KIND: rubeus.FILE,
                'name': _clean_file_name(fobj.path),
                'urls': {
                    'view': fobj.url(node),
                    'download': fobj.download_url(node),
                    'delete': fobj.api_url(node),
                },
                'permissions': {
                    'view': True,
                    'edit': can_edit,
                },
                'downloads': fobj.download_count(node),
                'size': [
                    float(fobj.size),
                    rubeus.format_filesize(fobj.size),
                ],
                'dates': {
                    'modified': [
                        time.mktime(fobj.date_modified.timetuple()),
                        fobj.date_modified.strftime('%Y/%m/%d %I:%M %p')
                    ],
                }
            }
            info.append(item)

    return info

@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def get_osffiles(auth, **kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    can_view = node.can_view(auth)

    info = []

    if can_view:
        for name, fid in node.files_current.iteritems():
            fobj = NodeFile.load(fid)
            item = {
                'name': _clean_file_name(fobj.path),
                'download': fobj.download_url(node),
                'size': rubeus.format_filesize(fobj.size),
                'date_modified': fobj.date_modified.strftime('%Y/%m/%d %I:%M %p'),
                'versions': node.files_versions[name]
            }
            info.append(item)

    return info

@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def get_osffiles_public(auth, **kwargs):

    node_settings = kwargs['node_addon']

    return get_osffiles_hgrid(node_settings, auth)


@must_be_valid_project  # returns project
@must_be_contributor_or_public  # returns user, project
@must_have_addon('osffiles', 'node')
def list_file_paths(**kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    return {'files': [
        NodeFile.load(fid).path
        for fid in node_to_use.files_current.values()
    ]}


@must_be_valid_project  # returns project
@must_have_permission(permissions.WRITE)  # returns user, project
@must_not_be_registration
@must_have_addon('osffiles', 'node')
def upload_file_public(auth, node_addon, **kwargs):

    node = kwargs['node'] or kwargs['project']

    do_redirect = request.form.get('redirect', False)

    name, content, content_type, size = prepare_file(request.files['file'])

    if size > (node_addon.config.max_file_size):
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': 'File too large.',
                'message_long': 'The file you are trying to upload exceeds '
                'the maximum file size limit.',
            },
        )

    try:
        fobj = node.add_file(
            auth,
            name,
            content,
            size,
            content_type
        )
    except FileNotModified:
        return {
            'actionTaken': None,
            'name': name,
        }

    # existing file was updated?
    was_updated = node.logs[-1].action == NodeLog.FILE_UPDATED
    unique, total = get_basic_counters(
        'download:{0}:{1}'.format(
            node._id,
            fobj.path.replace('.', '_')
        )
    )

    file_info = {
        'name': name,
        'size': [
            float(size),
            rubeus.format_filesize(size),
        ],

        # URLs
        'urls': {
            'view': fobj.url(node),
            'download': fobj.download_url(node),
            'delete': fobj.api_url(node),
        },

        rubeus.KIND: rubeus.FILE,
        'permissions': {
            'view': True,
            'edit': True,
        },

        'dates': {
            'uploaded': [
                time.mktime(fobj.date_uploaded.timetuple()),
                fobj.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            ],
        },

        'downloads': total or 0,
        'actionTaken': NodeLog.FILE_UPDATED if was_updated else NodeLog.FILE_ADDED,
    }

    if do_redirect:
        return redirect(request.referrer)

    return file_info, 201

@must_be_valid_project  # returns project
@must_be_contributor_or_public  # returns user, project
@must_have_addon('osffiles', 'node')
def file_info(auth, fid, **kwargs):
    versions = []
    node = kwargs['node'] or kwargs['project']
    file_name = fid
    file_name_clean = urlsafe_filename(file_name)
    files_page_url = node.web_url_for('collect_file_trees')
    latest_download_url = None
    api_url = None
    anonymous = has_anonymous_link(node, auth)

    try:
        files_versions = node.files_versions[file_name_clean]
    except KeyError:
        raise HTTPError(http.NOT_FOUND)
    latest_version_number = get_latest_version_number(file_name_clean, node) + 1

    for idx, version in enumerate(list(reversed(files_versions))):
        node_file = NodeFile.load(version)
        number = len(files_versions) - idx
        unique, total = get_basic_counters('download:{}:{}:{}'.format(
            node._primary_key,
            file_name_clean,
            number,
        ))
        download_url = node_file.download_url(node)
        api_url = node_file.api_url(node)
        versions.append({
            'file_name': file_name,
            'download_url': download_url,
            'version_number': number,
            'display_number': number if idx > 0 else 'current',
            'modified_date': node_file.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            'downloads': total if total else 0,
            'committer_name': privacy_info_handle(
                node_file.uploader.fullname, anonymous, name=True
            ),
            'committer_url': privacy_info_handle(node_file.uploader.url, anonymous),
        })
        if number == latest_version_number:
            latest_download_url = download_url
    return {
        'node_title': node.title,
        'file_name': file_name,
        'versions': versions,
        'registered': node.is_registration,
        'urls': {
            'api': api_url,
            'files': files_page_url,
            'latest': {
                'download': latest_download_url,
            },
        }
    }

@must_be_valid_project  # returns project
@must_be_contributor_or_public  # returns user, project
@must_have_addon('osffiles', 'node')
def view_file(auth, **kwargs):

    node_settings = kwargs['node_addon']
    node = kwargs['node'] or kwargs['project']

    file_name = kwargs['fid']
    file_name_clean = file_name.replace('.', '_')

    try:
        guid = OsfGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('name', 'eq', file_name)
        )
    except:
        guid = OsfGuidFile(
            node=node,
            name=file_name,
        )
        guid.save()

    redirect_url = check_file_guid(guid)
    if redirect_url:
        return redirect(redirect_url)

    # Throw 404 and log error if file not found in files_versions
    try:
        file_id = node.files_versions[file_name_clean][-1]
    except KeyError:
        logger.error('File {} not found in files_versions of component {}.'.format(
            file_name_clean, node._id
        ))
        raise HTTPError(http.NOT_FOUND)
    file_object = NodeFile.load(file_id)

    # Ensure NodeFile is attached to Node; should be fixed by actions or
    # improved data modeling in future
    if not file_object.node:
        file_object.node = node
        file_object.save()

    download_url = file_object.download_url(node)
    render_url = file_object.render_url(node)
    info_url = file_object.info_url(node)

    file_path = os.path.join(
        settings.UPLOADS_PATH,
        node._primary_key,
        file_name
    )
    # Throw 404 and log error if file not found on disk
    if not os.path.isfile(file_path):
        logger.error('File {} not found on disk.'.format(file_path))
        raise HTTPError(http.NOT_FOUND)

    _, file_ext = os.path.splitext(file_path.lower())

    # Get or create rendered file
    cache_file = get_cache_file(
        file_object.filename,
        file_object.latest_version_number(node)
    )
    rendered = get_cache_content(
        node_settings, cache_file, start_render=True, file_path=file_path,
        file_content=None, download_path=download_url,
    )

    rv = {
        'file_name': file_name,
        'render_url': render_url,
        'rendered': rendered,
        'info_url': info_url,
    }

    rv.update(_view_project(node, auth))
    return rv

FILE_NOT_FOUND_ERROR = HTTPError(http.NOT_FOUND, data=dict(
    message_short='File not found',
    message_long='The file you requested could not be found.'
))

@must_be_valid_project  # injects project
@must_be_contributor_or_public  # injects user, project
def download_file(fid, **kwargs):
    node = kwargs['node'] or kwargs['project']

    try:
        vid = get_latest_version_number(fid, node) + 1
    except FileNotFoundError:
        raise FILE_NOT_FOUND_ERROR
    redirect_url = node.web_url_for('download_file_by_version', fid=fid, vid=vid)
    return redirect(redirect_url)


@must_be_valid_project  # injects project
@must_be_contributor_or_public  # injects user, project
@update_counters('download:{target_id}:{fid}:{vid}')
@update_counters('download:{target_id}:{fid}')
def download_file_by_version(**kwargs):
    node = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']
    invalid_version_error = HTTPError(http.BAD_REQUEST, data=dict(
        message_short='Invalid version',
        message_long='The version number you requested is invalid.'
    ))
    try:
        version_number = int(kwargs['vid']) - 1
    except (TypeError, ValueError):
        raise invalid_version_error
    try:
        current_version = get_latest_version_number(filename, node=node)
    except FileNotFoundError:
        raise FILE_NOT_FOUND_ERROR

    try:
        file_object = node.get_file_object(filename, version=version_number)
    except InvalidVersionError:
        raise invalid_version_error
    except VersionNotFoundError:
        raise HTTPError(http.NOT_FOUND, data=dict(
            message_short='Version not found',
            message_long='The version number you requested could not be found.'
        ))
    content, content_type = node.read_file_object(file_object)
    if version_number == current_version:
        attachment_filename = filename
    else:
        filename_base, file_extension = os.path.splitext(file_object.path)
        attachment_filename = '{base}_{tmstp}{ext}'.format(
            base=filename_base,
            ext=file_extension,
            tmstp=file_object.date_uploaded.strftime('%Y%m%d%H%M%S')
        )
    return send_file(
        StringIO(content),
        mimetype=content_type,
        as_attachment=True,
        attachment_filename=attachment_filename,
    )


@must_be_valid_project  # injects project
@must_have_permission(permissions.WRITE)  # injects user, project
@must_not_be_registration
def delete_file(fid, auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    try:
        node.remove_file(auth, fid)
    except FileNotFoundError:
        raise FILE_NOT_FOUND_ERROR
    return {'message': 'Successfully deleted file'}


def get_cache_file(fid, vid):
    return '{0}_v{1}.html'.format(
        hashlib.md5(fid).hexdigest(),
        vid,
    )

@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def osffiles_get_rendered_file(**kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    cache_file = get_cache_file(kwargs['fid'], kwargs['vid'])
    return get_cache_content(node_settings, cache_file)


# todo will use later - JRS
# def check_celery(**kwargs):
#     celery_id = '/api/v1/project/{pid}/files/download/{fid}/version/{vid}/render'.format(
#         pid=kwargs['pid'], fid=kwargs['fid'],  vid=kwargs['vid']
#     )
#
#     if build_rendered_html.AsyncResult(celery_id).state == "SUCCESS":
#         cached_file_path = os.path.join(
#             settings.BASE_PATH, "cached", kwargs['pid'],
#             kwargs['fid'].replace('.', '_') + "_v" + kwargs['vid'] + ".html"
#         )
#         return open(cached_file_path, 'r').read()
#
#     if build_rendered_html.AsyncResult(celery_id).state == "FAILURE":
#         return '<div> This file failed to render (timeout) </div>'
#     return None
#
