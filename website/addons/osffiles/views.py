"""

"""

import os
import cgi
import time
from cStringIO import StringIO
import httplib as http
import logging

from framework import request, redirect, send_file, Q
from framework.git.exceptions import FileNotModified
from framework.exceptions import HTTPError
from framework.analytics import get_basic_counters, update_counters

from website.project.views.node import _view_project
from website.project.decorators import (
    must_not_be_registration, must_be_valid_project,
    must_be_contributor_or_public, must_have_addon, must_have_permission
)
from website.project.views.file import get_cache_content, prepare_file
from website.addons.base.views import check_file_guid
from website import settings
from website.project.model import NodeLog
from website.util import rubeus, permissions

from .model import NodeFile, OsfGuidFile

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
def get_osffiles(**kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']
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
def get_osffiles_public(**kwargs):

    node_settings = kwargs['node_addon']
    auth = kwargs['auth']

    return get_osffiles_hgrid(node_settings, auth)



@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@must_have_addon('osffiles', 'node')
def list_file_paths(**kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    return {'files': [
        NodeFile.load(fid).path
        for fid in node_to_use.files_current.values()
    ]}


@must_be_valid_project # returns project
@must_have_permission(permissions.WRITE)  # returns user, project
@must_not_be_registration
@must_have_addon('osffiles', 'node')
def upload_file_public(**kwargs):

    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']

    do_redirect = request.form.get('redirect', False)

    name, content, content_type, size = prepare_file(request.files['file'])

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

@must_be_valid_project #returns project
@must_be_contributor_or_public # returns user, project
@must_have_addon('osffiles', 'node')
def file_info(**kwargs):
    versions = []
    node = kwargs['node'] or kwargs['project']
    file_name = kwargs['fid']

    file_name_clean = file_name.replace('.', '_')

    try:
        files_versions = node.files_versions[file_name_clean]
    except KeyError:
        raise HTTPError(http.NOT_FOUND)
    for idx, version in enumerate(list(reversed(files_versions))):
        node_file = NodeFile.load(version)
        number = len(files_versions) - idx
        unique, total = get_basic_counters('download:{}:{}:{}'.format(
            node._primary_key,
            file_name_clean,
            number,
        ))
        versions.append({
            'file_name': file_name,
            'download_url': node_file.download_url(node),
            'version_number': number,
            'display_number': number if idx > 0 else 'current',
            'modified_date': node_file.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            'downloads': total if total else 0,
            'committer_name': node_file.uploader.fullname,
            'committer_url': node_file.uploader.url,
        })
    return {
        'files_url': node.url + "files/",
        'node_title': node.title,
        'file_name': file_name,
        'versions': versions,
    }

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
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
        'info_url': file_object.api_url(node) + 'info/',
    }

    rv.update(_view_project(node, auth))
    return rv


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(**kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']

    try:
        vid = len(node_to_use.files_versions[filename.replace('.', '_')])
    except KeyError:
        raise HTTPError(http.NOT_FOUND)

    redirect_url = '{url}osffiles/{fid}/version/{vid}/'.format(
        url=node_to_use.url,
        fid=filename,
        vid=vid,
    )
    return redirect(redirect_url)

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('download:{target_id}:{fid}:{vid}')
@update_counters('download:{target_id}:{fid}')
def download_file_by_version(**kwargs):
    node = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']

    version_number = int(kwargs['vid']) - 1
    current_version = len(node.files_versions[filename.replace('.', '_')]) - 1

    content, content_type = node.get_file(filename, version=version_number)
    if content is None:
        raise HTTPError(http.NOT_FOUND)

    if version_number == current_version:
        file_path = os.path.join(settings.UPLOADS_PATH, node._primary_key, filename)
        return send_file(
            file_path,
            mimetype=content_type,
            as_attachment=True,
            attachment_filename=filename,
        )

    file_object = node.get_file_object(filename, version=version_number)
    filename_base, file_extension = os.path.splitext(file_object.path)
    returned_filename = '{base}_{tmstp}{ext}'.format(
        base=filename_base,
        ext=file_extension,
        tmstp=file_object.date_uploaded.strftime('%Y%m%d%H%M%S')
    )
    return send_file(
        StringIO(content),
        mimetype=content_type,
        as_attachment=True,
        attachment_filename=returned_filename,
    )


@must_be_valid_project # returns project
@must_have_permission(permissions.WRITE) # returns user, project
@must_not_be_registration
def delete_file(**kwargs):

    auth = kwargs['auth']
    filename = kwargs['fid']
    node_to_use = kwargs['node'] or kwargs['project']

    if node_to_use.remove_file(auth, filename):
        return {}

    raise HTTPError(http.BAD_REQUEST)


def get_cache_file(fid, vid):
    return '{0}_v{1}.html'.format(
        fid.replace('.', '_'), vid,
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
