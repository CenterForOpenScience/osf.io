from framework import request, redirect, abort, secure_filename, send_file, get_basic_counters, update_counters
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from framework.auth import must_have_session_auth
from framework.git.exceptions import FileNotModified
from framework.auth import get_current_user, get_api_key
from ..model import NodeFile
from .node import _view_project

from framework import HTTPError
import httplib as http

from website import settings

import re
import pygments
import pygments.lexers
import pygments.formatters
import zipfile
import tarfile
from cStringIO import StringIO

import os


def prune_file_list(file_list, max_depth):
    if max_depth is None:
        return file_list
    return [file for file in file_list if len([c for c in file if c == '/']) <= max_depth]


@must_be_valid_project # returns project
def get_files(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    can_edit = node_to_use.can_edit(user, api_key)

    tree = {
        'title' : node_to_use.title if can_edit else node_to_use.public_title,
        'url' : node_to_use.url,
        'files' : [],
    }

    # Display children and files if public
    if can_edit or node_to_use.are_files_public:

        # Add child nodes
        for child in node_to_use.nodes:
            if not child.is_deleted:
                tree['files'].append({
                    'type': 'dir',
                    'url': child.url,
                    'api_url': child.api_url,
                })

        # Add files
        for key, value in node_to_use.files_current.iteritems():
            node_file = NodeFile.load(value)
            tree['files'].append({
                'type': 'file',
                'filename': node_file.filename,
                'path': node_file.path,
            })

    return tree


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def list_files(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    node_to_use = node or project

    return _view_project(node_to_use, user)

@must_be_valid_project # returns project
@must_be_contributor_or_public  # returns user, project
def upload_file_get(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    node_to_use = node or project

    file_infos = []
    for i, v in node_to_use.files_current.items():
        v = NodeFile.load(v)
        if not v.is_deleted:
            unique, total = get_basic_counters('download:' + node_to_use._primary_key + ':' + v.path.replace('.', '_') )
            file_infos.append({
                "name":v.path,
                "size":v.size,
                "url":node_to_use.url + "files/" + v.path,
                "type":v.content_type,
                "download_url": node_to_use.api_url + "/files/download/" + v.path,
                "date_uploaded": v.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
                "downloads": str(total) if total else str(0),
                "user_id": None,
                "user_fullname":None,
                "delete": v.is_deleted
            })
    return {'files' : file_infos}

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def upload_file_public(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    node_to_use = node or project
    api_key = get_api_key()

    uploaded_file = request.files.get('files[]')
    uploaded_file_content = uploaded_file.read()
    uploaded_file.seek(0, os.SEEK_END)
    uploaded_file_size = uploaded_file.tell()
    uploaded_file_content_type = uploaded_file.content_type
    uploaded_filename = secure_filename(uploaded_file.filename)

    try:
        file_object = node_to_use.add_file(
            user,
            api_key,
            uploaded_filename,
            uploaded_file_content,
            uploaded_file_size,
            uploaded_file_content_type
        )
    except FileNotModified as e:
        # TODO: Should raise a 400 but this breaks BlueImp
        return [{
            'action_taken' : None,
            'message' : e.message,
            'name' : uploaded_filename,
        }]

    unique, total = get_basic_counters('download:' + node_to_use._primary_key + ':' + file_object.path.replace('.', '_') )

    file_info = {
        "name":uploaded_filename,
        "size":uploaded_file_size,
        "url":node_to_use.url + "files/" + uploaded_filename + "/",
        "type":uploaded_file_content_type,
        "download_url":node_to_use.url + "/files/download/" + file_object.path,
        "date_uploaded": file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        "downloads": str(total) if total else str(0),
        "user_id": None,
        "user_fullname":None,
    }
    return [file_info], 201

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def view_file(*args, **kwargs):
    user = kwargs['user']
    node_to_use = kwargs['node'] or kwargs['project']

    file_name = kwargs['fid']
    file_name_clean = file_name.replace('.', '_')

    renderer = 'default'

    file_path = os.path.join(settings.uploads_path, node_to_use._primary_key, file_name)

    if not os.path.isfile(file_path):
        abort(http.NOT_FOUND)

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
            'file_name' : file_name,
            'number' : number,
            'display_number' : number if number > 0 else 'current',
            'date_uploaded' : node_file.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            'total' : total if total else 0,
        })

    file_size = os.stat(file_path).st_size
    if file_size > settings.max_render_size:

        rv = {
            'file_name' : file_name,
            'rendered' : 'This file is too large to be rendered online. Please download the file to view it locally.',
            'renderer' : renderer,
            'versions' : versions,

        }
        rv.update(_view_project(node_to_use, user))
        return rv
        # .encode('utf-8', 'replace')

    _, file_ext = os.path.splitext(file_path.lower())

    is_img = False
    for fmt in settings.img_fmts:
        fmt_ptn = '^.{0}$'.format(fmt)
        if re.search(fmt_ptn, file_ext):
            is_img = True
            break

    # todo: add bzip, etc
    if is_img:
        rendered="<img src='{node_url}files/download/{fid}/' />".format(node_url=node_to_use.api_url, fid=file_name)
    elif file_ext == '.zip':
        archive = zipfile.ZipFile(file_path)
        archive_files = prune_file_list(archive.namelist(), settings.archive_depth)
        archive_files = [secure_filename(fi) for fi in archive_files]
        file_contents = '\n'.join(['This archive contains the following files:'] + archive_files)
        file_path = 'temp.txt'
        renderer = 'pygments'
    elif file_path.lower().endswith('.tar') or file_path.endswith('.tar.gz'):
        archive = tarfile.open(file_path)
        archive_files = prune_file_list(archive.getnames(), settings.archive_depth)
        archive_files = [secure_filename(fi) for fi in archive_files]
        file_contents = '\n'.join(['This archive contains the following files:'] + archive_files)
        file_path = 'temp.txt'
        renderer = 'pygments'
    else:
        renderer = 'pygments'
        try:
            file_contents = open(file_path, 'r').read()
        except IOError:
            abort(http.NOT_FOUND)

    if renderer == 'pygments':
        try:
            rendered = pygments.highlight(
                file_contents,
                pygments.lexers.guess_lexer_for_filename(file_path, file_contents),
                pygments.formatters.HtmlFormatter()
            )
        except pygments.util.ClassNotFound:
            rendered = 'This type of file cannot be rendered online.  Please download the file to view it locally.'

    rv = {
        'file_name' : file_name,
        'rendered' : rendered,
        'renderer' : renderer,
        'versions' : versions,
    }
    rv.update(_view_project(node_to_use, user))
    return rv
    # ).encode('utf-8', 'replace')

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    filename = kwargs['fid']
    node_to_use = node or project

    kwargs["vid"] = len(node_to_use.files_versions[filename.replace('.', '_')])

    return redirect('{node_url}files/download/{fid}/version/{vid}/'.format(
        node_url=node_to_use.api_url,
        fid=kwargs['fid'],
        vid=kwargs['vid'],
    ))

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('download:{pid}:{fid}:{vid}')
@update_counters('download:{nid}:{fid}:{vid}')
@update_counters('download:{pid}:{fid}')
@update_counters('download:{nid}:{fid}')
def download_file_by_version(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    filename = kwargs['fid']
    version_number = int(kwargs['vid']) - 1

    node_to_use = node or project

    current_version = len(node_to_use.files_versions[filename.replace('.', '_')])
    if version_number == current_version:
        file_path = os.path.join(settings.uploads_path, node_to_use._primary_key, filename)
        return send_file(file_path)

    content, content_type = node_to_use.get_file(filename, version=version_number)
    if content is None:
        raise HTTPError(http.NOT_FOUND)
        # return abort(404)
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


@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def delete_file(*args, **kwargs):

    user = kwargs['user']
    api_key = get_api_key()
    filename = kwargs['fid']
    node_to_use = kwargs['node'] or kwargs['project']

    if node_to_use.remove_file(user, api_key, filename):
        return {'status' : 'success'}

    raise HTTPError(http.BAD_REQUEST)
    # return {'status' : 'failure'}

