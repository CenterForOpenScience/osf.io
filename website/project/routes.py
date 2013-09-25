from framework import (
    get, post, request, redirect, must_be_logged_in, push_status_message, abort,
    push_errors_to_status, app, render, Blueprint, get_user, get_current_user,
    secure_filename, jsonify, update_counters, send_file
)
from . import (
    new_node, new_project, get_node, show_diff, get_file_tree, prune_file_list,
)
from .decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from .forms import NewProjectForm, NewNodeForm
from .model import ApiKey, User, Tag, Node, NodeFile, NodeWikiPage, NodeLog
from framework.forms.utils import sanitize
from framework.git.exceptions import FileNotModified
from framework.auth import must_have_session_auth

from website import settings

from website import filters

from framework.analytics import get_basic_counters
from framework import analytics

from flask import Response, make_response

from BeautifulSoup import BeautifulSoup
import json
import os
import re
import difflib
import hashlib
import httplib as http
from cStringIO import StringIO

import pygments
import pygments.lexers
import pygments.formatters
import zipfile
import tarfile

mod = Blueprint('project', __name__, template_folder='templates')

def get_node_permission(node, user):
    return {
        'is_contributor' : node.is_contributor(user),
        'can_edit' : node.is_contributor(user) and not node.is_registration,
    }

@must_have_session_auth #
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def edit_node(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']

    node_to_use = node or project
    
    form = request.form
    original_title = node_to_use.title

    if form.get('name') == 'title' and form.get('value'):
        node_to_use.title = sanitize(form['value'])

        node_to_use.add_log(
            action='edit_title',
            params={
                'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                'node':node_to_use._primary_key,
                'title_new':node_to_use.title,
                'title_original':original_title,
            }, 
            user=get_current_user(),
        )

        node_to_use.save()

    return {'status' : 'success'}

def search_user(*args, **kwargs):
    form = request.form
    query = form.get('query', '').strip()

    is_email = False
    email_re = re.search('[^@\s]+@[^@\s]+\.[^@\s]+', query)
    if email_re:
        is_email = True
        email = email_re.group(0)
        result = User.find_by_email(email)
    else:
        result = User.search(query)

    return {
        'is_email':is_email,
        'results':[
            {
                'fullname' : item.fullname,
                'gravatar' : filters.gravatar(item.username, size=settings.gravatar_size_add_contributor),
                'id' : item._primary_key,
            } for item in result
        ]
    }

def project_tag(tag):
    backs = Tag.load(tag).node__tagged
    if backs:
        nodes = [obj for obj in backs if obj.is_public]
    else:
        nodes = []
    return {
        'nodes' : [
            {
                'title' : node.title,
                'url' : node.url(),
            }
            for node in nodes
        ]
    }

##############################################################################
# New Project
##############################################################################

@must_be_logged_in
def project_new(*args, **kwargs):
    form = NewProjectForm()
    return {
        'form' : form,
    }

@must_be_logged_in
def project_new_post(*args, **kwargs):
    user = kwargs['user']
    form = NewProjectForm(request.form)
    if form.validate():
        project = new_project(form.title.data, form.description.data, user)
        return redirect('/project/' + str(project._primary_key))
    else:
        push_errors_to_status(form.errors)
    return {
        'form' : form,
    }, http.BAD_REQUEST

##############################################################################
# New Node
##############################################################################

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_new_node(*args, **kwargs):
    form = NewNodeForm(request.form)
    project = kwargs['project']
    user = kwargs['user']
    if form.validate():
        node = new_node(
            title=form.title.data, 
            user=user, 
            category=form.category.data,
            project = project,
        )
        return redirect('/project/' + str(project._primary_key))
    else:
        push_errors_to_status(form.errors)
    # todo: raise error
    return redirect('/project/' + str(project._primary_key))

@must_be_valid_project
def node_fork_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
        push_status_message('At this time, only projects can be forked; however, this behavior is coming soon.')
        # todo discuss
        return redirect(node_to_use.url())
    else:
        node_to_use = project

    if node_to_use.is_registration:
        push_status_message('At this time, only projects that are not registrations can be forked; however, this behavior is coming soon.')
        # todo discuss
        return node_to_use.url()

    fork = node_to_use.fork_node(user)

    return fork.url()

template_name_replacements = {
    ('.txt', ''),
    (' ', '_'),
}
def clean_template_name(template_name):
    for replacement in template_name_replacements:
        template_name = template_name.replace(*replacement)
    return template_name

@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_page(*args, **kwargs):

    user = kwargs['user']
    node_to_use = kwargs['node'] or kwargs['project']

    content = ','.join([
        '"{}"'.format(clean_template_name(template_name))
        for template_name in os.listdir('website/static/registration_templates/')
    ])
    rv = {
        'content' : content,
    }
    rv.update(_view_project(node_to_use, user))
    return rv


@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
def node_register_tempate_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    template_name = kwargs['template'].replace(' ', '_').replace('.txt', '')
    # template_name_clean = clean_template_name(kwargs['template'])

    with open('website/static/registration_templates/' +  template_name + '.txt') as f:
        template = f.read()

    content = ','.join([
        '"{}"'.format(stored_template_name.replace('_', ' '))
        for stored_template_name in os.listdir('website/static/registration_templates/')
    ])

    if node_to_use.is_registration and node_to_use.registered_meta:
        form_values = node_to_use.registered_meta.get(template_name)
    else:
        form_values = None

    rv = {
        'content' : content,
        'template' : template,
        'template_name' : template_name,
        'form_values' : form_values
    }
    rv.update(_view_project(node_to_use, user))
    return rv

@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_tempate_page_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    data = request.form['data']
    parsed_data = json.loads(data)

    for k, v in parsed_data.items():
        if v is not None and v != sanitize(v):
            # todo interface needs to deal with this
            push_status_message('Invalid submission.')
            return json.dumps({
                'status' : 'error',
            })

    template = kwargs['template']

    register = node_to_use.register_node(user, template, data)

    # todo return 201
    return {
        'status' : 'success',
        'result' : register.url(),
    }

@must_have_session_auth
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_registrations(*args, **kwargs):

    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    return _view_project(node_to_use, user)

@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_forks(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    node_to_use = node or project
    return _view_project(node_to_use, user)

@must_be_valid_project
@must_be_contributor # returns user, project
def node_setting(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    node_to_use = node or project

    return _view_project(node_to_use, user)

##############################################################################
# View Project
##############################################################################

@must_be_valid_project
@must_not_be_registration
@must_be_contributor # returns user, project
def project_reorder_components(*args, **kwargs):
    project = kwargs['project']
    user = get_current_user()

    node_to_use = project
    old_list = [i._id for i in node_to_use.nodes if not i.is_deleted]
    new_list = json.loads(request.form['new_list'])

    if len(old_list) == len(new_list) and set(new_list) == set(old_list):
        node_to_use.nodes = new_list
        if node_to_use.save():
            return {'status' : 'success'}
    # todo log impossibility
    return {'success' : 'failure'}

##############################################################################

@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def project_statistics(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    # todo not used
    node_to_use = node or project

    counters = analytics.get_day_total_list(
        'node:{}'.format(node_to_use._primary_key)
    )
    csv = '\\n'.join(['date,price'] + ['{},{}'.format(counter[0], counter[1]) for counter in counters])

    rv = {
        'csv' : csv,
    }
    rv.update(_view_project(node_to_use, user))
    return rv

###############################################################################
# Make Public
###############################################################################


@must_have_session_auth
@must_be_valid_project
@must_be_contributor
def project_set_permissions(*args, **kwargs):

    user = kwargs['user']
    permissions = kwargs['permissions']
    node_to_use = kwargs['node'] or kwargs['project']

    node_to_use.set_permissions(permissions, user)

    # todo discuss behavior
    return redirect(node_to_use.url())

@get('/project/<pid>/watch')
@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_not_be_registration
def project_watch(*args, **kwargs):
    project = kwargs['project']
    user = kwargs['user']
    project.watch(user)
    return redirect('/project/'+str(project._primary_key))

@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addtag(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    tag = kwargs['tag']

    node_to_use.add_tag(tag=tag, user=user)

    return {'status' : 'success'}

@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removetag(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    tag = kwargs['tag']

    node_to_use.remove_tag(tag=tag, user=user)

    return {'status' : 'success'}

@must_have_session_auth # returns user or api_node
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def component_remove(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    # todo discuss behavior
    if node_to_use.remove_node(user=user):
        push_status_message('Component(s) deleted')
        return redirect('/dashboard/')
    else:
        push_status_message('Component(s) unable to be deleted')
        return redirect(node_to_use.url())

###############################################################################
# Add Contributors
###############################################################################
@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removecontributor(*args, **kwargs):

    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    if request.json['id'].startswith('nr-'):
        outcome = node_to_use.remove_nonregistered_contributor(user, request.json['name'], request.json['id'].replace('nr-', ''))    
    else:
        outcome = node_to_use.remove_contributor(user, request.json['id'])

    return {'status' : 'success' if outcome else 'failure'}

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributor_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    if "user_id" in request.form:
        user_id = request.form['user_id'].strip()
        added_user = get_user(id=user_id)
        if added_user:
            if user_id not in node_to_use.contributors:
                node_to_use.contributors.append(added_user)
                node_to_use.contributor_list.append({'id':added_user._primary_key})
                node_to_use.save()

                node_to_use.add_log(
                    action='contributor_added',
                    params={
                        'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                        'node':node_to_use._primary_key,
                        'contributors':[added_user._primary_key],
                    }, 
                    user=user,
                )
    elif "email" in request.form and "fullname" in request.form:
        # TODO: Nothing is done here to make sure that this looks like an email.
        # todo have same behavior as wtforms
        email = sanitize(request.form["email"].strip())
        fullname = sanitize(request.form["fullname"].strip())
        if email and fullname:
            node_to_use.contributor_list.append({'nr_name':fullname, 'nr_email':email})
            node_to_use.save()

        node_to_use.add_log(
            action='contributor_added',
            params={
                'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                'node':node_to_use._primary_key,
                'contributors':[{"nr_name":fullname, "nr_email":email}],
            }, 
            user=user,
        )

    return {'status' : 'success'}

# @post('/project/<pid>/addcontributors')
# @post('/project/<pid>/node/<nid>/addcontributors')
# @must_have_session_auth # returns user
# @must_be_valid_project # returns project
# @must_be_contributor # returns user, project
# @must_not_be_registration
# def project_addcontributors_post(*args, **kwargs):
#     project = kwargs['project']
#     node = kwargs['node']
#     user = kwargs['user']
#
#     node_to_use = node or project
#
#     emails = request.form['emails']
#     lines = emails.split('\r\n')
#     users = []
#     for line in lines:
#         elements = line.split(',')
#         email = elements[1]
#         fullname = elements[0]
#         temp_user = add_unclaimed_user(email, fullname)
#         if temp_user._primary_key not in node_to_use.contributors:
#             users.append(temp_user._primary_key)
#             node_to_use.contributors.append(temp_user)
#     node_to_use.save()
#     node_to_use.add_log(
#         action='contributor_added',
#         params={
#             'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
#             'node':node_to_use._primary_key,
#             'contributors':users,
#         },
#         user=user,
#     )
#
#     if node:
#         return redirect('/project/{pid}/node/{nid}'.format(pid=project._primary_key, nid=node._primary_key))
#     else:
#         return redirect('/project/{pid}'.format(pid=project._primary_key))

###############################################################################
# Files
###############################################################################

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def get_files(*args, **kwargs):

    user = kwargs['user']
    node_to_use = kwargs['node'] or kwargs['project']

    tree = {
        'title' : node_to_use.title,
        'url' : node_to_use.url(),
        'files' : [],
    }

    for child in node_to_use.nodes:
        if not child.is_deleted:
            tree['files'].append({
                'type' : 'dir',
                'url' : child.url(),
                'api_url' : child.api_url(),
            })

    if node_to_use.is_public or node_to_use.is_contributor(user):
        for key, value in node_to_use.files_current.iteritems():
            node_file = NodeFile.load(value)
            tree['files'].append({
                'type' : 'file',
                'filename' : node_file.filename,
                'path' : node_file.path,
            })

    return tree


@must_be_valid_project
def view_project(*args, **kwargs):
    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']
    return _view_project(node_to_use, user)

def _view_project(node_to_use, user):

    return {

        'node_id' : node_to_use._primary_key,
        'node_title' : node_to_use.title,
        'node_category' : node_to_use.category,
        'node_description' : node_to_use.description,
        'node_url' : node_to_use.url(),
        'node_api_url' : node_to_use.api_url(),
        'node_is_public' : node_to_use.is_public,
        'node_date_created' : node_to_use.date_created.strftime('%Y/%m/%d %I:%M %p'),
        'node_date_modified' : node_to_use.logs[-1].date.strftime('%Y/%m/%d %I:%M %p'),

        'node_tags' : [tag._primary_key for tag in node_to_use.tags],
        'node_children' : [
            {
                'child_id' : child._primary_key,
                'child_url' : child.url(),
                'child_api_url' : child.api_url(),
            }
            for child in node_to_use.nodes
        ],

        'node_is_registration' : node_to_use.is_registration,
        'node_registered_from_url' : node_to_use.registered_from.url() if node_to_use.is_registration else '',
        'node_registered_date' : node_to_use.registered_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_registration else '',
        'node_registered_meta' : [
            {
                'name_no_ext' : meta.replace('.txt', ''),
                'name_clean' : clean_template_name(meta),
            }
            for meta in node_to_use.registered_meta
        ],
        'node_registrations' : [
            {
                'registration_id' : registration._primary_key,
                'registration_url' : registration.url(),
                'registration_api_url' : registration.api_url(),
            }
            for registration in node_to_use.node__registered
        ],

        'node_is_fork' : node_to_use.is_fork,
        'node_forked_from_url' : node_to_use.forked_from.url() if node_to_use.is_fork else '',
        'node_forked_date' : node_to_use.forked_date.strftime('%Y/%m/%d %I:%M %p') if node_to_use.is_fork else '',
        'node_fork_count' : len(node_to_use.fork_list),
        'node_forks' : [
            {
                'fork_id' : fork._primary_key,
                'fork_url' : fork.url(),
                'fork_api_url' : fork.api_url(),
            }
            for fork in node_to_use.node__forked
        ],

        'parent_id' : node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
        'parent_title' : node_to_use.node__parent[0].title if node_to_use.node__parent else None,
        'parent_url' : node_to_use.node__parent[0].url() if node_to_use.node__parent else None,

        'user_is_contributor' : node_to_use.is_contributor(user),
        'user_can_edit' : node_to_use.is_contributor(user) and not node_to_use.is_registration,

    }


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
                "url":node_to_use.url() + "files/" + v.path,
                "type":v.content_type,
                "download_url": node_to_use.url() + "/files/download/" + v.path,
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

    uploaded_file = request.files.get('files[]')
    uploaded_file_content = uploaded_file.read()
    uploaded_file.seek(0, os.SEEK_END)
    uploaded_file_size = uploaded_file.tell()
    uploaded_file_content_type = uploaded_file.content_type
    uploaded_filename = secure_filename(uploaded_file.filename)
    
    try:
        file_object = node_to_use.add_file(
            user,
            uploaded_filename,
            uploaded_file_content,
            uploaded_file_size,
            uploaded_file_content_type
        )
    except FileNotModified as e:
        return [{
            'action_taken' : None,
            'message' : e.message,
            'name' : uploaded_filename,
        }]

    unique, total = get_basic_counters('download:' + node_to_use._primary_key + ':' + file_object.path.replace('.', '_') )

    file_info = {
        "name":uploaded_filename, 
        "size":uploaded_file_size, 
        "url":node_to_use.url() + "/files/" + uploaded_filename,
        "type":uploaded_file_content_type,
        "download_url":node_to_use.url() + "/files/download/" + file_object.path,
        "date_uploaded": file_object.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
        "downloads": str(total) if total else str(0),
        "user_id": None,
        "user_fullname":None,
    }
    return [file_info]

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
        rendered="<img src='{node_url}/files/download/{fid}' />".format(node_url=node_to_use.url(), fid=file_name)
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

@get('/project/<pid>/files/download/<fid>')
@get('/project/<pid>/node/<nid>/files/download/<fid>')
@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    filename = kwargs['fid']
    node_to_use = node or project
    
    kwargs["vid"] = len(node_to_use.files_versions[filename.replace('.', '_')])

    if node:
        return redirect('/project/{pid}/node/{nid}/files/download/{fid}/version/{vid}'.format(**kwargs))
    else:
        return redirect('/project/{pid}/files/download/{fid}/version/{vid}'.format(**kwargs))

@get('/project/<pid>/files/download/<fid>/version/<vid>')
@get('/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>')
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
        return abort(404)
    file_object = node_to_use.get_file_object(filename, version=version_number)
    filename_base, file_extension = os.path.splitext(file_object.path)
    returned_filename = '{base}_{tmstp}{ext}'.format(
        base=filename_base,
        ext=file_extension,
        tmstp=file_object.date_uploaded.strftime('%Y%m%d%H%M%S')
    )
    print returned_filename
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
    project, node, user, filename = kwargs['project'], kwargs['node'], kwargs['user'], kwargs['fid']

    node_to_use = node or project

    if node_to_use.remove_file(user, filename):
        return jsonify({'status' : 'success'})
    return jsonify({'status' : 'failure'})


###############################################################################
# Wiki
###############################################################################

def project_project_wikimain(pid):
    return redirect('/project/%s/wiki/home' % str(pid))

def project_node_wikihome(pid, nid):
    return redirect('/project/{pid}/node/{nid}/wiki/home'.format(pid=pid, nid=nid))

@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_wiki_compare(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']

    node_to_use = node or project

    pw = node_to_use.get_wiki_page(wid)

    if pw:
        compare_id = kwargs['compare_id']
        comparison_page = node_to_use.get_wiki_page(wid, compare_id)
        if comparison_page:
            current = pw.content
            comparison = comparison_page.content
            sm = difflib.SequenceMatcher(None, comparison, current)
            content = show_diff(sm)
            content = content.replace('\n', '<br />')
            versions = [NodeWikiPage.load(i) for i in reversed(node_to_use.wiki_pages_versions[wid])]
            versions_json = []
            for version in versions:
                versions_json.append({
                    'version' : version.version,
                    'user_fullname' : version.user.fullname,
                    'date' : version.date,
                })
            rv = {
                'pageName' : wid,
                'content' : content,
                'versions' : versions_json,
                'is_current' : True,
                'is_edit' : True,
                'version' : pw.version,
            }
            rv.update(_view_project(node_to_use, user))
            return rv
    push_status_message('Not a valid version')
    return redirect('{}wiki/{}'.format(
        node_to_use.url(),
        wid
    ))

@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_wiki_version(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']
    vid = kwargs['vid']

    node_to_use = node or project

    pw = node_to_use.get_wiki_page(wid, version=vid)

    if pw:
        rv = {
            'pageName' : wid,
            'content' : pw.html,
            'version' : pw.version,
            'is_current' : pw.is_current,
            'is_edit' : False,
        }
        rv.update(_view_project(node_to_use, user))
        return rv

    push_status_message('Not a valid version')
    return redirect('{}wiki/{}'.format(
        node_to_use.url(),
        wid
    ))

@must_be_valid_project # returns project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_wiki_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    wid = kwargs['wid']

    user = get_current_user()
    node_to_use = node or project

    if not node_to_use.is_public:
        if user:
            if not node_to_use.is_contributor(user):
                push_status_message('You are not a contributor on this page')
                return redirect('/')
        else:
            push_status_message('You are not authorized to view this page')
            return redirect('/account')

    pw = node_to_use.get_wiki_page(wid)

    # todo breaks on /<script>; why?

    if pw:
        version = pw.version
        is_current = pw.is_current
        content = pw.html
    else:
        version = 'NA'
        is_current = False
        content = 'There does not seem to be any content on this page; sorry.'

    toc = [
        {
            'id' : child._primary_key,
            'title' : child.title,
            'category' : child.category,
            'pages' : child.wiki_pages_current.keys() if child.wiki_pages_current else [],
        }
        for child in node_to_use.nodes
        if not child.is_deleted
    ]

    rv = {
        'pageName' : wid,
        'page' : pw,
        'version' : version,
        'content' : content,
        'is_current' : is_current,
        'is_edit' : False,
        'pages_current' : node_to_use.wiki_pages_versions.keys(),
        'toc' : toc,
    }
    rv.update(_view_project(node_to_use, user))
    return rv

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_wiki_edit(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']

    node_to_use = node or project

    pw = node_to_use.get_wiki_page(wid)

    if pw:
        version = pw.version
        is_current = pw.is_current
        content = pw.content
    else:
        version = 'NA'
        is_current = False
        content = ''
    rv = {
        'pageName' : wid,
        'page' : pw,
        'version' : version,
        'content' : content,
        'is_current' : is_current,
        'is_edit' : True,
    }
    rv.update(_view_project(node_to_use, user))
    return rv

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_wiki_edit_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']

    if node:
        node_to_use = node
        base_url = '/project/{pid}/node/{nid}/wiki'.format(pid=project._primary_key, nid=node._primary_key)
    else:
        node_to_use = project
        base_url = '/project/{pid}/wiki'.format(pid=project._primary_key)

    if wid != sanitize(wid):
        push_status_message("This is an invalid wiki page name")
        return redirect(base_url)

    node_to_use.updateNodeWikiPage(wid, request.form['content'], user)

    return redirect(base_url + '/{wid}'.format(wid=wid))

app.register_blueprint(mod)

@must_have_session_auth
@must_be_contributor_or_public
def get_contributors(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    contributors = []
    for contributor in node_to_use.contributor_list:
        if 'id' in contributor:
            user = User.load(contributor['id'])
            contributors.append({
                'registered' : True,
                'id' : user._primary_key,
                'fullname' : user.fullname,
            })
        else:
            contributors.append({
                'registered' : False,
                'id' : hashlib.md5(contributor['nr_email']).hexdigest(),
                'fullname' : contributor['nr_name'],
            })

    return {'contributors' : contributors}


@must_be_valid_project
def get_logs(*args, **kwargs):
    project = kwargs['project']
    logs = list(reversed(project.logs._to_primary_keys()))
    if 'count' in kwargs:
        logs = logs[:kwargs['count']]
    return logs

@must_be_valid_project
def get_summary(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    return {
        'summary' : {
            'pid' : node_to_use._primary_key,
            'purl' : node_to_use.url(),
            'title' : node_to_use.title,
            'registered_date' : node_to_use.registered_date.strftime('%m/%d/%y %I:%M %p') if node_to_use.registered_date else None,
            'logs' : list(reversed(node_to_use.logs._to_primary_keys()))[:3],
        }
    }


def _render_log_contributor(contributor):
    if isinstance(contributor, dict):
        rv = contributor.copy()
        rv.update({'registered' : False})
        return rv
    user = User.load(contributor)
    return {
        'id' : user._primary_key,
        'fullname' : user.fullname,
        'registered' : True,
    }

def get_log(log_id):

    log = NodeLog.load(log_id)
    user = get_current_user()
    node_to_use = Node.load(log.params.get('node')) or Node.load(log.params.get('project'))

    if not node_to_use.is_public and not node_to_use.is_contributor(user):
        return {
            'status' : 'failure',
        }

    # api_key = ApiKey.load(log.api_key)
    project = Node.load(log.params.get('project'))
    node = Node.load(log.params.get('node'))

    log_json = {
        'user_id' : log.user._primary_key if log.user else '',
        'user_fullname' : log.user.fullname if log.user else '',
        'api_key' : log.api_key.label if log.api_key else '',
        'project_url' : project.url() if project else '',
        'node_url' : node.url() if node else '',
        'project_title' : project.title if project else '',
        'node_title' : node.title if node else '',
        'action' : log.action,
        'params' : log.params,
        'category' : 'project' if log.params['project'] else 'component',
        'date' : log.date.strftime('%m/%d/%y %I:%M %p'),
        'contributors' : [_render_log_contributor(contributor) for contributor in log.params.get('contributors', [])],
        'contributor' : _render_log_contributor(log.params.get('contributor', {})),
    }
    return {'log' : log_json}

@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def get_node_keys(*args, **kwargs):
    node_to_use = kwargs['node'] or kwargs['project']
    return {
        'keys' : [
            {
                'key' : key._id,
                'label' : key.label,
            }
            for key in node_to_use.api_keys
        ]
    }

@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def create_node_key(*args, **kwargs):

    # Generate key
    api_key = ApiKey(label=request.form['label'])
    api_key.save()

    # Append to node
    node_to_use = kwargs['node'] or kwargs['project']
    node_to_use.api_keys.append(api_key)
    node_to_use.save()

    # Return response
    return {'response' : 'success'}

@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def revoke_node_key(*args, **kwargs):

    # Load key
    api_key = ApiKey.load(request.form['key'])

    # Remove from user
    node_to_use = kwargs['node'] or kwargs['project']
    node_to_use.api_keys.remove(api_key)
    node_to_use.save()

    # Send response
    return {'response' : 'success'}

@must_have_session_auth
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def node_key_history(*args, **kwargs):

    api_key = ApiKey.load(kwargs['kid'])
    user = get_current_user()
    node_to_use = kwargs['node'] or kwargs['project']

    rv = {
        'key' : api_key._id,
        'label' : api_key.label,
        'route' : '/settings',
        'logs' : [
            {
                'lid' : log._id,
                'nid' : log.node__logged[0]._id,
                'route' : log.node__logged[0].url(),
            }
            for log in api_key.nodelog__created
        ]
    }

    rv.update(_view_project(node_to_use, user))
    return rv