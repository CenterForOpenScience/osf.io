"""

"""

import os
import cgi
import time
from cStringIO import StringIO
import httplib as http
import logging

from hurry.filesize import size, alternative

from framework import request, redirect, secure_filename, send_file
from framework.git.exceptions import FileNotModified
from framework.exceptions import HTTPError
from framework.analytics import get_basic_counters, update_counters
from website.project.views.node import _view_project
from website.project.decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public, must_have_addon
from website.project.views.file import get_cache_content
from website import settings

from .model import NodeFile

logger = logging.getLogger(__name__)


@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def osffiles_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    osffiles = node.get_addon('osffiles')
    rv = {
        'complete': True,
    }
    rv.update(osffiles.config.to_json())
    return rv

###

def _clean_file_name(name):
    " HTML-escape file name and encode to UTF-8. "
    escaped = cgi.escape(name)
    encoded = unicode(escaped).encode('utf-8')
    return encoded



def osffiles_dummy_folder(node_settings, auth, parent=None, **kwargs):

    node = node_settings.owner
    can_view = node.can_view(auth)
    can_edit = node.can_edit(auth)
    return {
        'addon': 'OSF Files',
        'kind': 'folder',
        'accept': {
            'maxSize': node_settings.config.max_file_size,
        },
        'name': 'OSF Files',
        'urls': {
            'upload': os.path.join(node.api_url, 'osffiles') + '/',
            'fetch': os.path.join(node.api_url, 'osffiles', 'hgrid') + '/',
        },
        'permissions': {
            'view': can_view,
            'edit': can_edit,
        },
    }


@must_be_contributor_or_public
@must_have_addon('osffiles', 'node')
def get_osffiles(*args, **kwargs):

    node_settings = kwargs['node_addon']
    node = node_settings.owner
    auth = kwargs['auth']

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    info = []

    if can_view:

        for name, fid in node.files_current.iteritems():

            fobj = NodeFile.load(fid)
            unique, total = get_basic_counters(
                'download:{0}:{1}'.format(
                    node_settings.owner._id,
                    fobj.path.replace('.', '_')
                )
            )

            item = {
                'kind': 'file',
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
                'downloads': total or 0,
                'size': [
                    float(fobj.size),
                    size(fobj.size, system=alternative)
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


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@must_have_addon('osffiles', 'node')
def list_file_paths(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    return {'files': [
        NodeFile.load(fid).path
        for fid in node_to_use.files_current.values()
    ]}


@must_be_valid_project # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
@must_have_addon('osffiles', 'node')
def upload_file_public(*args, **kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node = kwargs['node'] or kwargs['project']

    do_redirect = request.form.get('redirect', False)

    uploaded_file = request.files.get('file')
    uploaded_file_content = uploaded_file.read()
    uploaded_file.seek(0, os.SEEK_END)
    uploaded_file_size = uploaded_file.tell()
    uploaded_file_content_type = uploaded_file.content_type
    uploaded_filename = secure_filename(uploaded_file.filename)

    try:
        fobj = node.add_file(
            auth,
            uploaded_filename,
            uploaded_file_content,
            uploaded_file_size,
            uploaded_file_content_type
        )
    except FileNotModified as e:
        return [{
            'action_taken': None,
            'message': e.message,
            'name': uploaded_filename,
        }]

    unique, total = get_basic_counters(
        'download:{0}:{1}'.format(
            node._id,
            fobj.path.replace('.', '_')
        )
    )

    file_info = {
        'name': uploaded_filename,
        'size': [
            float(uploaded_file_size),
            size(uploaded_file_size, system=alternative),
        ],

        # URLs
        'urls': {
            'view': fobj.url(node),
            'download': fobj.download_url(node),
            'delete': fobj.api_url(node),
        },

        'kind': 'file',
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
    }

    if do_redirect:
        return redirect(request.referrer)

    return [file_info], 201

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@must_have_addon('osffiles', 'node')
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def view_file(*args, **kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node_to_use = kwargs['node'] or kwargs['project']

    file_name = kwargs['fid']
    file_name_clean = file_name.replace('.', '_')

    # Throw 404 and log error if file not found in files_versions
    try:
        file_id = node_to_use.files_versions[file_name_clean][-1]
    except KeyError:
        logger.error('File {} not found in files_versions of component {}.'.format(
            file_name_clean, node_to_use._id
        ))
        raise HTTPError(http.NOT_FOUND)
    file_object = NodeFile.load(file_id)

    # Ensure NodeFile is attached to Node; should be fixed by actions or
    # improved data modeling in future
    if not file_object.node:
        file_object.node = node_to_use
        file_object.save()

    download_path = file_object.download_url(node_to_use)

    file_path = os.path.join(
        settings.UPLOADS_PATH,
        node_to_use._primary_key,
        file_name
    )
    # Throw 404 and log error if file not found on disk
    if not os.path.isfile(file_path):
        logger.error('File {} not found on disk.'.format(file_path))
        raise HTTPError(http.NOT_FOUND)

    versions = []

    for idx, version in enumerate(list(reversed(node_to_use.files_versions[file_name_clean]))):
        node_file = NodeFile.load(version)
        number = len(node_to_use.files_versions[file_name_clean]) - idx
        unique, total = get_basic_counters('download:{}:{}:{}'.format(
            node_to_use._primary_key,
            file_name_clean,
            number,
        ))
        versions.append({
            'file_name': file_name,
            'number': number,
            'display_number': number if idx > 0 else 'current',
            'date_uploaded': node_file.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            'total': total if total else 0,
            'committer_name': node_file.uploader.fullname,
            'committer_url': node_file.uploader.url,
        })

    _, file_ext = os.path.splitext(file_path.lower())

    # Get or create rendered file
    cache_file = get_cache_file(
        file_object.filename,
        file_object.latest_version_number
    )
    rendered = get_cache_content(
        node_settings, cache_file, start_render=True, file_path=file_path,
        file_content=None, download_path=download_path,
    )

    rv = {
        'file_name': file_name,
        'render_url': download_path + 'render/',
        'rendered': rendered,
        'versions': versions,
    }
    rv.update(_view_project(node_to_use, auth))
    return rv


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']

    vid = len(node_to_use.files_versions[filename.replace('.', '_')])

    return redirect('{url}osffiles/{fid}/version/{vid}/'.format(
        url=node_to_use.api_url,
        fid=filename,
        vid=vid,
    ))


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('download:{pid}:{fid}:{vid}')
@update_counters('download:{nid}:{fid}:{vid}')
@update_counters('download:{pid}:{fid}')
@update_counters('download:{nid}:{fid}')
def download_file_by_version(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']

    version_number = int(kwargs['vid']) - 1
    current_version = len(node_to_use.files_versions[filename.replace('.', '_')]) - 1

    content, content_type = node_to_use.get_file(filename, version=version_number)
    if content is None:
        raise HTTPError(http.NOT_FOUND)

    if version_number == current_version:
        file_path = os.path.join(settings.UPLOADS_PATH, node_to_use._primary_key, filename)
        return send_file(
            file_path,
            mimetype=content_type,
            as_attachment=True,
            attachment_filename=filename,
        )

    file_object = node_to_use.get_file_object(filename, version=version_number)
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
@must_be_contributor # returns user, project
@must_not_be_registration
def delete_file(*args, **kwargs):

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
def osffiles_get_rendered_file(*args, **kwargs):
    """

    """
    node_settings = kwargs['node_addon']
    cache_file = get_cache_file(kwargs['fid'], kwargs['vid'])
    return get_cache_content(node_settings, cache_file)


# todo will use later - JRS
# def check_celery(*args, **kwargs):
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
