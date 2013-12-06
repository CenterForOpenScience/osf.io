import re
import os
import cgi
import json
import time
import zipfile
import tarfile
from cStringIO import StringIO
import httplib as http
import logging

import pygments
import pygments.lexers
import pygments.formatters
from hurry.filesize import size, alternative

from framework import request, redirect, secure_filename, send_file
from framework.auth import must_have_session_auth
from framework.git.exceptions import FileNotModified
from framework.auth import get_current_user, get_api_key
from framework.exceptions import HTTPError
from framework.analytics import get_basic_counters, update_counters
from website.project.views.node import _view_project
from website.project.decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from website.project.model import NodeFile
from website import settings

logger = logging.getLogger(__name__)

def prune_file_list(file_list, max_depth):
    if max_depth is None:
        return file_list
    return [file for file in file_list if len([c for c in file if c == '/']) <= max_depth]


def get_file_tree(node_to_use, user):
    tree = []
    for node in node_to_use.nodes:
        if not node.is_deleted:
            tree.append(get_file_tree(node, user))

    if node_to_use.can_view(user):
        for i,v in node_to_use.files_current.items():
            v = NodeFile.load(v)
            tree.append(v)

    return (node_to_use, tree)


@must_be_valid_project # returns project
@must_be_contributor_or_public
def get_files(*args, **kwargs):
    """Build list of files for HGrid, ignoring contents of components to which
    the user does not have access. Note: This view hides the titles of
    inaccessible components but includes their GUIDs.

    """
    # Get arguments
    node_to_use = kwargs['node'] or kwargs['project']
    user = get_current_user()

    filetree = get_file_tree(node_to_use, user)
    parent_id = node_to_use.parent_id

    rv = _get_files(filetree, parent_id, 0, user)
    rv['info'] = json.dumps(rv['info'])
    if not kwargs.get('dash', False):
        rv.update(_view_project(node_to_use, user))
    return rv

def _clean_file_name(name):
    " HTML-escape file name and encode to UTF-8. "
    escaped = cgi.escape(name)
    encoded = unicode(escaped).encode('utf-8')
    return encoded

def _get_files(filetree, parent_id, check, user):
    if parent_id is not None:
        parent_uid = 'node-{}'.format(parent_id)
    else:
        parent_uid = 'null'

    info = []
    itemParent = {}
    itemParent['uid'] = '-'.join([
            "node",  # node or nodefile
            str(filetree[0]._id)  # ObjectId from pymongo
        ])
    itemParent['isComponent'] = "true"
    itemParent['parent_uid'] = parent_uid
    if str(filetree[0].category)=="project" or itemParent['parent_uid']=="null":
        itemParent['uploadUrl'] = str(itemParent['uid'].split('-')[1]).join([ #join
            '/api/v1/project/',
            '/files/upload/'
        ])
    else:
        parent_id = itemParent['parent_uid'].split('-')[1]
        itemParent['uploadUrl'] = str('/').join([
            '/api/v1/project',
            str(parent_id),
            'node',
            str(filetree[0]._id),
            'files/upload/'
        ])
    itemParent['type'] = "folder"
    itemParent['size'] = "0"
    itemParent['sizeRead'] = '--'
    itemParent['dateModified'] = '--'
    parent_type = filetree[0].project_or_component.capitalize()
    itemParent['name'] = _clean_file_name(
        u'{}: {}'.format(
            parent_type, filetree[0].title
        )
    )
    itemParent['can_edit'] = str(
        filetree[0].is_contributor(user) and
        not filetree[0].is_registration
    ).lower()
    itemParent['can_view'] = str(filetree[0].can_view(user)).lower()
    if itemParent['can_view'] == 'false':
        itemParent['name'] = 'Private Component'
    if check == 0:
        itemParent['parent_uid'] = "null"
    info.append(itemParent)
    if itemParent['can_view'] == 'true':
        for tmp in filetree[1]:
            if isinstance(tmp, tuple):
                info = info + _get_files(
                    filetree=tmp,
                    parent_id=filetree[0]._id,
                    check=1,
                    user=user
                )['info']
            else:
                unique, total = get_basic_counters('download:' + str(filetree[0]._id) + ':' + tmp.path.replace('.', '_') )
                item = {}
                item['uid'] = '-'.join([
                    "nodefile",  # node or nodefile
                    str(tmp._id)  # ObjectId from pymongo
                ])
                item['downloads'] = total if total else 0
                item['isComponent'] = "false"
                item['parent_uid'] = str(itemParent['uid'])
                item['type'] = "file"
                item['name'] = _clean_file_name(tmp.path)
                item['ext'] = _clean_file_name(tmp.path.split('.')[-1])
                item['sizeRead'] = [
                    float(tmp.size),
                    size(tmp.size, system=alternative)
                ]
                item['size'] = str(tmp.size)
                item['url'] = 'files/'.join([
                    str(filetree[0].deep_url),
                    item['name'] + '/'
                ])
                item['dateModified'] = [
                    time.mktime(tmp.date_modified.timetuple()),
                    tmp.date_modified.strftime('%Y/%m/%d %I:%M %p')
                ]
                info.append(item)
    return {'info': info}


@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def list_file_paths(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']

    return {'files': [
        NodeFile.load(fid).path
        for fid in node_to_use.files_current.values()
    ]}


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
                "name": v.path,
                "size": v.size,
                "url": node_to_use.url + "files/" + v.path,
                "type": v.content_type,
                "download_url": node_to_use.api_url + "files/download/" + v.path,
                "date_uploaded": v.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
                "downloads": total if total else 0,
                "user_id": None,
                "user_fullname": None,
                "delete": v.is_deleted,
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
    do_redirect = request.form.get('redirect', False)

    uploaded_file = request.files.get('file')
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
        "sizeRead": [
            float(uploaded_file_size),
            size(uploaded_file_size, system=alternative),
        ],
        "size":str(uploaded_file_size),
        "url":node_to_use.url + "files/" + uploaded_filename + "/",
        "ext":str(uploaded_filename.split('.')[-1]),
        "type":"file",
        "download_url":node_to_use.url + "/files/download/" + file_object.path,
        "date_uploaded": file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        "dateModified": [
            time.mktime(file_object.date_uploaded.timetuple()),
            file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        ],
        "downloads": total if total else 0,
        "user_id": None,
        "user_fullname":None,
        "uid": '-'.join([
            str(file_object._name), #node or nodefile
            str(file_object._id) #objectId
        ]),
        "parent_uid": '-'.join([
            "node",
            str(node_to_use._id)
        ])
    }

    if do_redirect:
        return redirect(request.referrer)

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

    # Throw 404 and log error if file not found in files_versions
    try:
        latest_node_file_id = node_to_use.files_versions[file_name_clean][-1]
    except KeyError:
        logger.error('File {} not found in files_versions of component {}.'.format(
            file_name_clean, node_to_use._id
        ))
        raise HTTPError(http.NOT_FOUND)
    latest_node_file = NodeFile.load(latest_node_file_id)

    # Ensure NodeFile is attached to Node; should be fixed by actions or
    # improved data modeling in future
    if not latest_node_file.node:
        latest_node_file.node = node_to_use
        latest_node_file.save()

    download_path = latest_node_file.download_url
    download_html = '<a href="{path}">Download file</a>'.format(path=download_path)

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
            'file_name' : file_name,
            'number' : number,
            'display_number' : number if idx > 0 else 'current',
            'date_uploaded' : node_file.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
            'total' : total if total else 0,
        })

    file_size = os.stat(file_path).st_size
    if file_size > settings.MAX_RENDER_SIZE:

        rv = {
            'file_name' : file_name,
            'rendered' : ('<p>This file is too large to be rendered online. '
                        'Please <a href={path}>download the file</a> to view it locally.</p>'
                        .format(path=download_path)),
            'renderer' : renderer,
            'versions' : versions,

        }
        rv.update(_view_project(node_to_use, user))
        return rv

    _, file_ext = os.path.splitext(file_path.lower())

    is_img = False
    for fmt in settings.IMG_FMTS:
        fmt_ptn = '^.{0}$'.format(fmt)
        if re.search(fmt_ptn, file_ext):
            is_img = True
            break


    # TODO: this logic belongs in model
    # todo: add bzip, etc
    if is_img:
        rendered="<img src='{node_url}files/download/{fid}/' />".format(node_url=node_to_use.api_url, fid=file_name)
    elif file_ext == '.zip':
        archive = zipfile.ZipFile(file_path)
        archive_files = prune_file_list(archive.namelist(), settings.ARCHIVE_DEPTH)
        archive_files = [secure_filename(fi) for fi in archive_files]
        file_contents = '\n'.join(['This archive contains the following files:'] + archive_files)
        file_path = 'temp.txt'
        renderer = 'pygments'
    elif file_path.lower().endswith('.tar') or file_path.endswith('.tar.gz'):
        archive = tarfile.open(file_path)
        archive_files = prune_file_list(archive.getnames(), settings.ARCHIVE_DEPTH)
        archive_files = [secure_filename(fi) for fi in archive_files]
        file_contents = '\n'.join(['This archive contains the following files:'] + archive_files)
        file_path = 'temp.txt'
        renderer = 'pygments'
    else:
        renderer = 'pygments'
        try:
            file_contents = open(file_path, 'r').read()
        except IOError:
            raise HTTPError(http.NOT_FOUND)

    if renderer == 'pygments':
        try:
            rendered = download_html + pygments.highlight(
                file_contents,
                pygments.lexers.guess_lexer_for_filename(file_path, file_contents),
                pygments.formatters.HtmlFormatter()
            )
        except pygments.util.ClassNotFound:
            rendered = ('<p>This file cannot be rendered online. '
                        'Please <a href={path}>download the file</a> to view it locally.</p>'
                        .format(path=download_path))

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
        fid=filename,
        vid=kwargs['vid'],
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

