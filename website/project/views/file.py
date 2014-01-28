<<<<<<< HEAD
import os
import cgi
import json
import time
from cStringIO import StringIO
import httplib as http
import logging

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
from framework.render.tasks import build_rendered_html


logger = logging.getLogger(__name__)


def prune_file_list(file_list, max_depth):
    if max_depth is None:
        return file_list
    return [file for file in file_list if len([c for c in file if c == '/']) <= max_depth]
=======
"""

"""
>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c

import json

from framework.flask import request
from framework.auth import get_current_user

<<<<<<< HEAD
    if node_to_use.can_view(user):
        for i, v in node_to_use.files_current.items():
            v = NodeFile.load(v)
            tree.append(v)
    return node_to_use, tree
=======
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project

>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c

def _get_dummy_container(node, user, parent=None):
    """Create HGrid JSON for a dummy component container.

    :return dict: HGrid-formatted dummy container

    """
<<<<<<< HEAD
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
@must_be_contributor_or_public  # returns user, project
def upload_file_get(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    file_infos = []
    for i, v in node_to_use.files_current.items():
        v = NodeFile.load(v)
        if not v.is_deleted:
            unique, total = get_basic_counters('download:{0}:{1}'.format(
                node_to_use._id,
                v.path.replace('.', '_'),
            ))
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
    return {'files': file_infos}


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
            'action_taken': None,
            'message': e.message,
            'name': uploaded_filename,
        }]

    unique, total = get_basic_counters('download:' + node_to_use._primary_key + ':' + file_object.path.replace('.', '_') )

    file_info = {
        "name": uploaded_filename,
        "sizeRead": [
            float(uploaded_file_size),
            size(uploaded_file_size, system=alternative),
        ],
        "size": str(uploaded_file_size),
        "url": node_to_use.url + "files/" + uploaded_filename + "/",
        "ext": str(uploaded_filename.split('.')[-1]),
        "type": "file",
        "download_url": node_to_use.url + "/files/download/" + file_object.path,
        "date_uploaded": file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        "dateModified": [
            time.mktime(file_object.date_uploaded.timetuple()),
            file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        ],
        "downloads": total if total else 0,
        "user_id": None,
        "user_fullname": None,
        "uid": '-'.join([
            str(file_object._name), #node or nodefile
            str(file_object._id) #objectId
        ]),
        "parent_uid": '-'.join([
            "node",
            str(node_to_use._id)
        ])
=======
    can_view = node.can_view(user)
    return {
        'uid': 'node:{0}'.format(node._id),
        'parent_uid': parent if parent else 'null',
        'name': 'Component: {0}'.format(node.title)
            if can_view
            else 'Private Component',
        'type': 'folder',
        'can_edit': node.can_edit(user) if can_view else False,
        'can_view': can_view,
        # Can never drag into component dummy folder
        'permission': False,
        'lazyLoad': node.api_url + 'files/',
>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c
    }


def _collect_file_trees(node, user, parent='null', **kwargs):
    """Collect file trees for all add-ons implementing HGrid views. Create
    dummy containers for each child of the target node, and for each add-on
    implementing HGrid views.

    :return list: List of HGrid-formatted file trees

<<<<<<< HEAD
    file_name = kwargs['fid']
    file_name_clean = file_name.replace('.', '_')
=======
    """
    grid_data = []
>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c

    # Collect add-on file trees
    for addon in node.get_addons():
        if addon.config.has_hgrid_files:
            dummy = addon.config.get_hgrid_dummy(
                addon, user, parent, **kwargs
            )
            # Skip if dummy folder is falsy
            if dummy:
                # Add add-on icon URL if specified
                dummy['iconUrl'] = addon.config.icon_url
                grid_data.append(dummy)

    # Collect component file trees
    for child in node.nodes:
        container = _get_dummy_container(child, user, parent)
        grid_data.append(container)

    return grid_data

<<<<<<< HEAD
    file_path = os.path.join(
        settings.UPLOADS_PATH,
        node_to_use._primary_key,
        file_name
    )
    # Throw 404 and log error if file not found on disk
    if not os.path.isfile(file_path):
        logger.error('File {} not found on disk.'.format(file_path))
        raise HTTPError(http.NOT_FOUND)
=======

def _collect_tree_js(node):
    """Collect JavaScript includes for all add-ons implementing HGrid views.
>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c

    :return list: List of JavaScript include paths

    """
    scripts = []
    for addon in node.get_addons():
        scripts.extend(addon.config.include_js.get('files', []))
    return scripts

<<<<<<< HEAD
    _, file_ext = os.path.splitext(file_path.lower())

    # Build cached paths and name
    vid = str(len(node_to_use.files_versions[file_name.replace('.', '_')]))

    cached_name = file_name_clean + "_v" + vid

    cached_file_path = os.path.join(
        settings.BASE_PATH, "cached",
        node_to_use._primary_key, cached_name + ".html"
    )

    cached_dir = cached_file_path.strip(cached_file_path.split('/')[-1])

    # Makes path if none exists
    if not os.path.exists(cached_file_path):

        # TODO: Move to celery or someplace reusable
        # TODO: Try / except; see http://stackoverflow.com/questions/273192/create-directory-if-it-doesnt-exist-for-file-write
        if not os.path.exists(cached_dir):
            os.makedirs(cached_dir)

        rendered = '<img src="/static/img/loading.gif">'

        is_rendered = False
        # build_rendered_html(file_path, cached_file_path, download_path)
        build_rendered_html.delay(file_path, cached_file_path, download_path)
    else:
        rendered = open(cached_file_path, 'r').read()
        is_rendered = True

    rv = {
        'file_name': file_name,
        'download_path': download_path,
        'rendered': rendered,
        'is_rendered': is_rendered,
        'versions': versions,
    }
    rv.update(_view_project(node_to_use, user))
    return rv

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    filename = kwargs['fid']

    vid = len(node_to_use.files_versions[filename.replace('.', '_')])

    return redirect('{url}files/download/{fid}/version/{vid}/'.format(
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
=======

@must_be_contributor_or_public
def collect_file_trees(*args, **kwargs):
    """Collect file trees for all add-ons implementing HGrid views, then
    format data as appropriate.

    """
    node = kwargs['node'] or kwargs['project']
    mode = kwargs.get('mode')
    user = get_current_user()
    data = request.args.to_dict()

    grid_data = _collect_file_trees(node, user, **data)
    if mode == 'page':
        rv = _view_project(node, user)
        rv.update({
            'grid_data': json.dumps(grid_data),
            'tree_js': _collect_tree_js(node),
        })
        return rv
    elif mode == 'widget':
        return {'grid_data': grid_data}
    else:
        return grid_data
>>>>>>> 561af2692d6e3c81dfe3bc390e8bf2cdbaf9a75c
