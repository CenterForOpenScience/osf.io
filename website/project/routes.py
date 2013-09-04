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
from .model import User, Tag, NodeFile, NodeWikiPage
from framework.git.exceptions import FileNotModified

from website import settings

from website import settings
from website import filters

from framework.analytics import get_basic_counters

from flask import Response, make_response

from website import settings

from BeautifulSoup import BeautifulSoup
import json
import os
import re
import scrubber
import markdown
import difflib
import httplib as http
from markdown.extensions.wikilinks import WikiLinkExtension
import pygments
from cStringIO import StringIO

mod = Blueprint('project', __name__, template_folder='templates')

@post('/project/<pid>/edit')
@post('/project/<pid>/node/<nid>/edit')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def edit_node(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
    else:
        node_to_use = project
    
    form = request.form
    original_title = node_to_use.title

    if form['name'] == 'title' and not form['value'].strip() == '':
        node_to_use.title = form['value']

        node_to_use.add_log('edit_title', 
            params={
                'project':node_to_use.node_parent.id if node_to_use.node_parent else None,
                'node':node_to_use.id,
                'title_new':node_to_use.title,
                'title_original':original_title,
            }, 
            user=user,
        )

        node_to_use.save()

    return jsonify({'response': 'success'})
    #if 'title' in request.json:
    #    
    #    node_to_use.save()

@post('/search/users/')
def search_user(*args, **kwargs):
    form = request.form
    query = form["query"].strip()

    is_email = False
    email_re = re.search('[^@\s]+@[^@\s]+\.[^@\s]+', query)
    if email_re:
        is_email = True
        email = email_re.group(0)
        result = User.find_by_email(email)
    else:
        result = User.search(query)

    return json.dumps({
        'is_email':is_email, 
        'results':[
            {
                'fullname' : item['fullname'],
                'gravatar' : filters.gravatar(item['username'], size=settings.gravatar_size_add_contributor),
                'id' : item['_id'],
            } for item in result
        ]
    })

@get('/tag/<tag>')
def project_tag(tag):
    backs = Tag.load(tag).node_tagged
    if backs:
        nodes = [obj for obj in backs.objects() if obj.is_public]
    else:
        nodes = None
    return render(filename='tags.mako', tag=tag, nodes=nodes)

##############################################################################
# New Project
##############################################################################

@get('/project/new')
@must_be_logged_in
def project_new(*args, **kwargs):
    user = kwargs['user']
    form = NewProjectForm()    
    return render(filename='project.new.mako', form=form)

@post('/project/new')
@must_be_logged_in
def project_new_post(*args, **kwargs):
    user = kwargs['user']
    form = NewProjectForm(request.form)
    if form.validate():
        project = new_project(form.title.data, form.description.data, user)
        return redirect('/project/' + str(project.id))
    else:
        push_errors_to_status(form.errors)
    return render(filename='project.new.mako', form=form)

##############################################################################
# New Node
##############################################################################

@post('/project/<pid>/newnode')
@must_be_logged_in # returns user
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
        return redirect('/project/' + str(project.id))
    else:
        push_errors_to_status(form.errors)
    return redirect('/project/' + str(project.id))

@post('/project/<pid>/fork')
@post('/project/<pid>/node/<nid>/fork')
@must_be_valid_project
def node_fork_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
        push_status_message('At this time, only projects can be forked; however, this behavior is coming soon.')
        return redirect(node_to_use.url())
    else:
        node_to_use = project

    if node_to_use.is_registration:
        push_status_message('At this time, only projects that are not registrations can be forked; however, this behavior is coming soon.')
        return node_to_use.url()

    fork = node_to_use.fork_node(user)

    return fork.url()

@get('/project/<pid>/register/')
@get('/project/<pid>/node/<nid>/register/')
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    if node:
        node_to_use = node
    else:
        node_to_use = project

    return render(
        filename='project.register.mako', 
        project=project,
        node=node,
        node_to_use=node_to_use,
        user=user,
    )

@get('/project/<pid>/register/<template>')
@get('/project/<pid>/node/<nid>/register/<template>')
@must_be_valid_project
@must_be_contributor # returns user, project
def node_register_tempate_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = ifelse(node, node, project)

    template_name = kwargs['template'].replace(' ', '_')

    with open('website/static/registration_templates/' +  template_name + '.txt') as f:
        template = f.read()

    if node_to_use.is_registration and node_to_use.registered_meta and template_name in node_to_use.registered_meta:
        return render(
            filename='project.register.mako',
            project=project,
            node=node,
            node_to_use=node_to_use,
            user=user,
            template = template,
            form_values=node_to_use.registered_meta[template_name],
        )
    else:
        return render(
            filename='project.register.mako',
            project=project,
            node=node,
            node_to_use=node_to_use,
            user=user,
            template = template,
        )


@post('/project/<pid>/register/<template>')
@post('/project/<pid>/node/<nid>/register/<template>')
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_tempate_page_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = ifelse(node, node, project)

    data = request.form['data']

    template = kwargs['template']

    register = node_to_use.register_node(user, template, data)
    
    return json.dumps({
        'result':register.url()
    })

@get('/project/<pid>/registrations')
@get('/project/<pid>/node/<nid>/registrations')
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_registrations(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
    else:
        node_to_use = project

    return render(
        filename='project.registrations.mako', 
        project=project,
        node=node,
        node_to_use=node_to_use,
        user=user,
    )

def ifelse(l,a,b):
    if l:
        return a
    else:
        return b

@get('/project/<pid>/forks')
@get('/project/<pid>/node/<nid>/forks')
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def node_forks(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    node_to_use = ifelse(node, node, project)

    return render(
        filename='project.forks.mako', 
        project=project,
        node=node,
        node_to_use=node_to_use,
        user=user,
    )

@get('/project/<pid>/settings')
@get('/project/<pid>/node/<nid>/settings')
@must_be_valid_project
@must_be_contributor # returns user, project
def node_setting(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
    else:
        node_to_use = project

    return render(
        filename='project.settings.mako', 
        project=project,
        node=node,
        node_to_use=node_to_use,
        user=user,
    )

##############################################################################
# View Project
##############################################################################

@post('/api/v1/reorder_components/<pid>')
@must_be_valid_project
@must_be_contributor # returns user, project
def project_reorder_components(*args, **kwargs):
    project = kwargs['project']
    user = get_current_user()

    node_to_use = project
    print node_to_use.nodes
    old_list = [i._id for i in node_to_use.nodes.objects() if not i.is_deleted]
    new_list = json.loads(request.form['new_list'])

    if len(set(old_list).intersection(set(new_list))) == len(old_list):
        from yORM.Object import Object
        node_to_use.nodes = Object.ObjectList(
            node_to_use.nodes.parent,
            node_to_use.nodes.name,
            node_to_use.nodes.type,
            new_list
        )

        if node_to_use.save():
            print node_to_use.nodes
            return jsonify({'success':'true'})

    return jsonify({'success':'false'})

@get('/project/<pid>/')
@get('/project/<pid>/node/<nid>/')
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_view(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
    else:
        node_to_use = project

    # If the node is a project, redirect to the project's page at the top level.
    if node and node_to_use.category == 'project':
        return redirect('/project/{}/'.format(node.id))

    #import pdb; pdb.set_trace()

    pw = node_to_use.get_wiki_page('home')
    if pw:
        wiki_home = pw.html
        wiki_home = BeautifulSoup(wiki_home[0:500] + '...')
    else:
        wiki_home="<p>No content</p>"

    return render(
        filename='project.dashboard.mako', 
        project=project,
        node=node,
        node_to_use=node_to_use,
        user=user,
        wiki_home=wiki_home,
        files = get_file_tree(node_to_use, user)
    )

#@mod.route('/project/<pid>/jeff')
#@update_counters('/project/.*?/')
#@must_be_valid_project
#def jeff(*args, **kwargs):
#    project = kwargs['project']
#    return render_template("project.html", project=project, scripts=['a', 'b'])
#
##############################################################################

@get('/project/<pid>/statistics')
@get('/project/<pid>/node/<nid>/statistics')
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def project_statistics(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = get_current_user()

    if node:
        node_to_use = node
    else:
        node_to_use = project

    return render(
        filename='project.statistics.mako', 
        project=project, 
        node=node,
        user=user,)


###############################################################################
# Make Public
###############################################################################


#TODO: project_makepublic and project_makeprivate should be refactored into a single function to conform to DRY.
@get('/project/<pid>/makepublic')
@get('/project/<pid>/node/<nid>/makepublic')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def project_makepublic(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    if node:
        node_to_use = node
        url = '/project/{pid}/node/{nid}'.format(pid=project.id, nid=node.id)
    else:
        node_to_use = project
        url = '/project/{pid}'.format(pid=project.id)

    if not node_to_use.is_public:             # if not already public
        node_to_use.makePublic(user)

    return redirect(url)

@get('/project/<pid>/makeprivate')
@get('/project/<pid>/node/<nid>/makeprivate')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
def project_makeprivate(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    if node:
        node_to_use = node
        url = '/project/{pid}/node/{nid}'.format(pid=project.id, nid=node.id)
    else:
        node_to_use = project
        url = '/project/{pid}'.format(pid=project.id)

    if node_to_use.is_public:
        node_to_use.makePrivate(user)

    return redirect(url)

@get('/project/<pid>/watch')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_not_be_registration
def project_watch(*args, **kwargs):
    project = kwargs['project']
    user = kwargs['user']
    project.watch(user)
    return redirect('/project/'+str(project.id))

@get('/project/<pid>/addtag/<tag>')
@get('/project/<pid>/node/<nid>/addtag/<tag>')
@must_be_logged_in
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

    return jsonify({'response': 'success'})

@get('/project/<pid>/removetag/<tag>')
@get('/project/<pid>/node/<nid>/removetag/<tag>')
@must_be_logged_in
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

    return jsonify({'response': 'success'})

@post('/project/<pid>/remove')
@post('/project/<pid>/node/<nid>/remove')
@must_be_logged_in
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

    if node_to_use.remove_node(user=user):
        push_status_message('Component(s) deleted')
        return redirect('/dashboard')
    else:
        push_status_message('Component(s) unable to be deleted')
        return redirect(node_to_use.url())

###############################################################################
# Add Contributors
###############################################################################
@post('/project/<pid>/removecontributors')
@post('/project/<pid>/node/<nid>/removecontributors')
@must_be_logged_in
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removecontributor(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    if request.json['id'].startswith('nr-'):
        outcome = node_to_use.remove_nonregistered_contributor(user, request.json['name'], request.json['id'].replace('nr-', ''))    
    else:
        outcome = node_to_use.remove_contributor(user, request.json['id'])
    return jsonify({'response': 'success'})

@post('/project/<pid>/addcontributor')
@post('/project/<pid>/node/<nid>/addcontributor')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributor_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    if node:
        node_to_use = node
    else:
        node_to_use = project

    if "user_id" in request.form:
        user_id = request.form['user_id'].strip()
        added_user = get_user(id=user_id)
        if added_user:
            if user_id not in node_to_use.contributors:
                node_to_use.contributors.append(added_user)
                node_to_use.contributor_list.append({'id':added_user.id})
                node_to_use.save()

                node_to_use.add_log('contributor_added', 
                    params={
                        'project':get_node(node_to_use.node_parent).id if node_to_use.node_parent else None,
                        'node':node_to_use.id,
                        'contributors':[added_user.id],
                    }, 
                    user=user,
                )
    elif "email" in request.form and "fullname" in request.form:
        email = request.form["email"].strip()
        fullname = request.form["fullname"].strip()
        if email and fullname:
            node_to_use.contributor_list.append({'nr_name':fullname, 'nr_email':email})
            node_to_use.save()

        node_to_use.add_log('contributor_added', 
            params={
                'project':get_node(node_to_use.node_parent).id if node_to_use.node_parent else None,
                'node':node_to_use.id,
                'contributors':[{"nr_name":fullname, "nr_email":email}],
            }, 
            user=user,
        )

    return json.dumps({
        'result':True,
    })

@post('/project/<pid>/addcontributors')
@post('/project/<pid>/node/<nid>/addcontributors')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributors_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    if node:
        node_to_use = node
    else:
        node_to_use = project

    emails = request.form['emails']
    lines = emails.split('\r\n')
    users = []
    for line in lines:
        elements = line.split(',')
        email = elements[1]
        fullname = elements[0]
        temp_user = add_unclaimed_user(email, fullname)
        if temp_user.id not in node_to_use.contributors:
            users.append(temp_user.id)
            node_to_use.contributors.append(temp_user)
    node_to_use.save()
    node_to_use.add_log('contributor_added', 
        params={
            'project':get_node(node_to_use.node_parent).id if node_to_use.node_parent else None,
            'node':node_to_use.id,
            'contributors':users,
        }, 
        user=user,
    )

    if node:
        return redirect('/project/{pid}/node/{nid}'.format(pid=project.id, nid=node.id))
    else:
        return redirect('/project/{pid}'.format(pid=project.id))

###############################################################################
# Files
###############################################################################

@get('/project/<pid>/files')
@get('/project/<pid>/node/<nid>/files')
@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def list_files(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    return render(
        filename='project.files.mako', 
        project=project,
        node=node,
        user=user,
        node_to_use=node_to_use
    )

@get('/project/<pid>/files/upload')
@get('/project/<pid>/node/<nid>/files/upload')
@must_be_valid_project # returns project
@must_be_contributor_or_public  # returns user, project
def upload_file_get(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    file_infos = []
    for i, v in node_to_use.files_current.items():
        v = NodeFile.load(v)
        if not v.is_deleted:
            unique, total = get_basic_counters('download:' + node_to_use.id + ':' + v.path.replace('.', '_') )
            file_infos.append({
                "name":v.path,
                "size":v.size,
                "url":node_to_use.url() + "/files/" + v.path,
                "type":v.content_type,
                "download_url": node_to_use.url() + "/files/download/" + v.path,
                "date_uploaded": v.date_uploaded.strftime('%Y/%m/%d %I:%M %p'),
                "downloads": str(total) if total else str(0),
                "user_id": None,
                "user_fullname":None,
                "delete": v.is_deleted
            })
    return jsonify(files=file_infos)

@post('/project/<pid>/files/upload')
@post('/project/<pid>/node/<nid>/files/upload')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def upload_file_public(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

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
        return Response(
            json.dumps([{
                'action_taken': None,
                'message': e.message,
                'name': uploaded_filename,
            }]),
            status=200,
            mimetype='application/json'
        )

    unique, total = get_basic_counters('download:' + node_to_use.id + ':' + file_object.path.replace('.', '_') )

    file_infos = []
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
    file_infos.append(file_info)
    resp = Response(json.dumps([file_info]), status=200, mimetype='application/json')
    return resp

from pygments.lexers import guess_lexer, guess_lexer_for_filename
from pygments import highlight
from pygments.formatters import HtmlFormatter
import zipfile
import tarfile

@get('/project/<pid>/files/<fid>')
@get('/project/<pid>/node/<nid>/files/<fid>')
@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def view_file(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    if node:
        node_to_use = node
    else:
        node_to_use = project

    file_name = kwargs['fid']

    renderer = 'default'

    file_path = os.path.join(settings.uploads_path, node_to_use.id, file_name)

    if not os.path.isfile(file_path):
        abort(http.NOT_FOUND)

    file_size = os.stat(file_path).st_size
    if file_size > settings.max_render_size:

        return render(
            filename='project.file.mako',
            project=project,
            node=node,
            user=user,
            node_to_use=node_to_use,
            file_name=file_name,
            rendered='This file is too large to be rendered online. Please download the file to view it locally.',
            renderer=renderer
        ).encode('utf-8', 'replace')

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
        file_contents = '\n'.join(['This archive contains the following files:'] + archive_files)
        file_path = 'temp.txt'
        renderer = 'pygments'
    elif file_path.lower().endswith('.tar') or file_path.endswith('.tar.gz'):
        archive = tarfile.open(file_path)
        archive_files = prune_file_list(archive.getnames(), settings.archive_depth)
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
            rendered = highlight(file_contents,guess_lexer_for_filename(file_path, file_contents), HtmlFormatter())
        except pygments.util.ClassNotFound:
            rendered = 'This type of file cannot be rendered online.  Please download the file to view it locally.'

    #if not file_path.endswith('.txt'):
    #    renderer = 'prettify'
    #else:
    #    renderer = 'txt'

    return render(
        filename='project.file.mako', 
        project=project,
        node=node,
        user=user,
        node_to_use=node_to_use,
        file_name=file_name,
        rendered=rendered,
        renderer=renderer,
    ).encode('utf-8', 'replace')

@get('/project/<pid>/files/download/<fid>')
@get('/project/<pid>/node/<nid>/files/download/<fid>')
@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
def download_file(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    filename = kwargs['fid']
    if node:
        node_to_use = node
    else:
        node_to_use = project
    
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

    if node:
        node_to_use = node
    else:
        node_to_use = project

    current_version = len(node_to_use.files_versions[filename.replace('.', '_')])
    if version_number == current_version:
        file_path = os.path.join(settings.uploads_path, node_to_use.id, filename)
        return send_file(file_path)

    content, content_type = node_to_use.get_file(filename, version=version_number)
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


#TODO: These should be DELETEs, not POSTs
@post('/project/<pid>/files/delete/<fid>')
@post('/project/<pid>/node/<nid>/files/delete/<fid>')
@must_be_logged_in
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def delete_file(*args, **kwargs):
    project, node, user, filename = kwargs['project'], kwargs['node'], kwargs['user'], kwargs['fid']

    node_to_use = node or project

    if node_to_use.remove_file(user, filename):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})



###############################################################################
# Wiki
###############################################################################

@get('/project/<pid>/wiki/')
def project_project_wikimain(pid):
    return redirect('/project/%s/wiki/home' % str(pid))

@get('/project/<pid>/node/<nid>/wiki/')
def project_node_wikihome(pid, nid):
    return redirect('/project/{pid}/node/{nid}/wiki/home'.format(pid=pid, nid=nid))

@get('/project/<pid>/wiki/<wid>/compare/<compare_id>')
@get('/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>')
@must_be_valid_project # returns project
@must_be_contributor_or_public # returns user, project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_wiki_compare(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']

    if node:
        node_to_use = node
    else:
        node_to_use = project

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
            return render(
                filename='project.wiki.compare.mako', 
                pageName=wid, 
                project=project, 
                node=node, 
                user=user, 
                content=content, 
                versions=versions,
                is_current=True, 
                is_edit=True, 
                version=pw.version
            )
    push_status_message('Not a valid version')
    if node:
        return redirect('/project/{pid}/node/{nid}/wiki/{wid}'.format(pid=project.id, nid=node.id, wid=wid))
    else:
        return redirect('/project/{pid}/wiki/{wid}'.format(pid=project.id, wid=wid))

@get('/project/<pid>/wiki/<wid>/version/<vid>')
@get('/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>')
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

    if node:
        node_to_use = node
    else:
        node_to_use = project

    pw = node_to_use.get_wiki_page(wid, version=vid)

    if pw:
        return render(
            filename='project.wiki.mako', 
            project=project, 
            node=node, 
            user=user, 
            pageName=wid, 
            content=pw.html,
            version=pw.version, 
            is_current=pw.is_current,
            is_edit=False)

    push_status_message('Not a valid version')
    if node:
        return redirect('/project/{pid}/node/{nid}/wiki/{wid}'.format(pid=project.id, nid=node.id, wid=wid))
    else:
        return redirect('/project/{pid}/wiki/{wid}'.format(pid=project.id, wid=wid))

@get('/project/<pid>/wiki/<wid>')
@get('/project/<pid>/node/<nid>/wiki/<wid>')
@must_be_valid_project # returns project
@update_counters('node:{pid}')
@update_counters('node:{nid}')
def project_wiki_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    wid = kwargs['wid']

    user = get_current_user()
    if node:
        node_to_use = node
    else:
        node_to_use = project

    if not node_to_use.is_public:
        if user:
            if not node_to_use.is_contributor(user):
                push_status_message('You are not a contributor on this page')
                return redirect('/')
        else:
            push_status_message('You are not authorized to view this page')
            return redirect('/account')

    pw = node_to_use.get_wiki_page(wid)

    if pw:
        version = pw.version
        is_current = pw.is_current
        content = pw.html
    else:
        version = 'NA'
        is_current = False
        content = 'There does not seem to be any content on this page; sorry.'

    return render(
        filename='project.wiki.mako', 
        project=project, 
        node=node, 
        user=user, 
        pageName=wid, 
        page=pw, 
        version=version,
        content=content, 
        is_current=is_current, 
        is_edit=False
    )

@get('/project/<pid>/wiki/<wid>/edit')
@get('/project/<pid>/node/<nid>/wiki/<wid>/edit')
@must_be_logged_in # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_wiki_edit(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    wid = kwargs['wid']

    if node:
        node_to_use = node
    else:
        node_to_use = project

    pw = node_to_use.get_wiki_page(wid)

    if pw:
        version = pw.version
        is_current = pw.is_current
        content = pw.content
    else:
        version = 'NA'
        is_current = False
        content = ''
    return render(
        filename='project.wiki.edit.mako', 
        project=project,
        node=node, 
        user=user, 
        pageName=wid, 
        page=pw, 
        version=version,
        content=content, 
        is_current=is_current, 
        is_edit=True
    )

@post('/project/<pid>/wiki/<wid>/edit')
@post('/project/<pid>/node/<nid>/wiki/<wid>/edit')
@must_be_logged_in # returns user
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
    else:
        node_to_use = project

    node_to_use.updateNodeWikiPage(wid, request.form['content'], user)

    if node:
        return redirect('/project/{pid}/node/{nid}/wiki/{wid}'.format(pid=project.id, nid=node.id, wid=wid))
    else:
        return redirect('/project/{pid}/wiki/{wid}'.format(pid=project.id, wid=wid))

app.register_blueprint(mod)