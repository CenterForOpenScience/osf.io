from framework.flask import app, request, make_response
from framework.mako import makolookup
from mako.template import Template
import framework
from website.models import Node
from website.project import get_file_tree
from website import settings
from framework import get_current_user

import json
import os
import pystache
import re
import lxml.html

def nonwrapped_fn(fn, keywords):
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapped

def wrapped_fn(fn, wrapper, fn_kwargs, wrapper_kwargs):
    def wrapped(*args, **kwargs):
        return wrapper(fn(*args, **kwargs), **wrapper_kwargs)
    return wrapped


# todo check if response
def call_url(url, wrap=True):

    func_name, func_data = app.url_map.bind('').match(url)
    view_function = view_functions[func_name]
    ret_val = view_function(**func_data)

    if wrap and not isinstance(ret_val, dict):
        if wrap is True:
            wrap = view_function.__name__
            wrap = re.sub('^get_', '', wrap)
        ret_val = {wrap : ret_val}

    return ret_val

view_functions = {}

def process_urls(app, urls):
    for u in urls:
        url = u[0]
        method = u[1]
        fn = u[2]

        wrapper, fn_kwargs, wrapper_kwargs = None, None, None

        if len(u) > 3:
            wrapper = u[3]
        if len(u) > 4:
            fn_kwargs = u[4]
        if len(u) > 5:
            wrapper_kwargs = u[5]

        if wrapper:
            view_func = wrapped_fn(fn, wrapper, fn_kwargs, wrapper_kwargs)
        else:
            view_func = nonwrapped_fn(fn, fn_kwargs)

        view_functions[wrapper.__name__ + '__' + fn.__name__] = fn

        app.add_url_rule(
            url,
            endpoint=wrapper.__name__ + '__' + fn.__name__,
            view_func=view_func,
            methods=[method]
        )

from modularodm import StoredObject
class ODMEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, StoredObject):
            return obj._primary_key
        return json.JSONEncoder.default(self, obj)

def jsonify(data, label=None):
    return json.dumps({label:data} if label else data, cls=ODMEncoder),
    # return app.response_class(
    #     json.dumps({label:data} if label else data, cls=ODMEncoder),
    #     mimetype='application/json'
    # )

# todo move
def get_display_name(username):
    if username:
        if len(username) > 22:
            return '%s...%s' % (username[:9],username[-10:])
        return username

# todo allow multiply wrapped functions in process_urls
def get_globals():
    user = get_current_user()
    return {
        'username' : user.username if user else '',
        'display_name' : get_display_name(user.username) if user else '',
        'use_cdn' : settings.use_cdn_for_client_libs,
        'dev_mode' : settings.dev_mode,
        'allow_login' : settings.allow_login,
    }

def render(data, template_file, renderer):

    data.update(get_globals())

    rendered = load_file(template_file)
    rendered = renderer(rendered, data)

    html = lxml.html.fragment_fromstring(rendered, create_parent='removeme')

    for el in html.findall('.//*[@mod-meta]'):
        element_attributes = el.attrib
        attributes_string = element_attributes['mod-meta']
        element_meta = json.loads(attributes_string) # todo more robust jsonqa

        is_replace = element_meta.get("replace", False)

        render_data = data.copy()

        kwargs = element_meta.get('kwargs', {})
        render_data.update(kwargs)

        uri = element_meta.get('uri')
        if uri:
            render_data.update(call_url(uri))

        # template_rendered = renderer(
        #     load_file(element_meta["tpl"]),
        #     render_data
        # )
        template_rendered = render(
            render_data,
            element_meta['tpl'],
            renderer
        )

        original = lxml.html.tostring(el)
        if is_replace:
            replacement = template_rendered
        else:
            replacement = lxml.html.tostring(el)
            replacement = replacement.replace('><', '>'+template_rendered+'<')

        rendered = rendered.replace(original, replacement)

    return rendered

def load_file(template_file):
    with open(os.path.join('static/templates/', template_file), 'r') as f:
        loaded = f.read()
    return loaded

def render_mustache_string(tpl_string, data):
    return pystache.render(tpl_string, context=data)

def render_jinja_string(tpl, data):
    pass

mako_cache = {}
def render_mako_string(tplname, data):
    tpl = mako_cache.get(tplname)
    if tpl is None:
        tpl = Template(tplname, lookup=makolookup)
        mako_cache[tplname] = tpl
    return tpl.render(**data)

def view_index():

    display_name = username = framework.get_current_username()
    if username and len(username) > 22:
        display_name = '%s...%s' % (username[:9],username[-10:])

    return {
        'username': username,
        'display_name': display_name,
        'status': framework.status.pop_status_messages(),
    }

def view_project(**kwargs):
    project = Node.load(kwargs['pid'])
    node = None
    user = framework.get_current_user()

    return {
        'project': project,
        'user': user,
        'node_to_use': project,
        'files': get_file_tree(project, user)
    }

def view_component(**kwargs):
    project = Node.load(kwargs['pid'])
    component = Node.load(kwargs['nid']) if kwargs.get('nid') else None
    user = framework.get_current_user()

    return {
        'project': project,
        'node': component,
        'user': user,
        'node_to_use': component,
        'files': get_file_tree(component, user)
    }

from website.profile import routes as profile_routes
from website.project import routes as project_routes

# Profile

# Web

process_urls(app, [
    ('/profile/', 'get', profile_routes.profile_view, render, {}, {'template_file' : 'profile.html', 'renderer' : render_mako_string}),
    ('/profile/<uid>/', 'get', profile_routes.profile_view_id, render, {}, {'template_file' : 'profile.html', 'renderer' : render_mako_string}),
    ('/settings/', 'get', profile_routes.profile_settings, render, {}, {'template_file' : 'settings.html', 'renderer' : render_mako_string}),
    ('/settings/key_history/<kid>/', 'get', profile_routes.user_key_history, render, {}, {'template_file' : 'key_history.html', 'renderer' : render_mako_string}),
    ('/profile/<uid>/edit/', 'post', profile_routes.edit_profile, jsonify, {}, {})
])

# API

process_urls(app, [
    ('/api/v1/profile/', 'get', profile_routes.profile_view, jsonify, {}, {}),
    ('/api/v1/profile/<uid>', 'get', profile_routes.profile_view_id, jsonify, {}, {}),
    ('/api/v1/profile/<uid>/public_projects/', 'get', profile_routes.get_public_projects, jsonify, {}, {}),
    ('/api/v1/profile/<uid>/public_components/', 'get', profile_routes.get_public_components, jsonify, {}, {}),
    ('/api/v1/settings/', 'get', profile_routes.profile_settings, jsonify, {}, {}),
    ('/api/v1/settings/keys/', 'get', profile_routes.get_keys, jsonify, {}, {}),
    ('/api/v1/settings/create_key/', 'post', profile_routes.create_user_key, jsonify, {}, {}),
    ('/api/v1/settings/revoke_key/', 'post', profile_routes.revoke_user_key, jsonify, {}, {}),
    ('/api/v1/settings/key_history/<kid>/', 'get', profile_routes.user_key_history, jsonify, {}, {}),
])

# Project

# Web

process_urls(app, [
    ('/', 'get', view_index, render, {}, {'template_file':'index.html', 'renderer':render_mako_string}),
    ('/project/<pid>/', 'get', view_project, render, {}, {'template_file':'project.html', 'renderer':render_mako_string}),
    ('/project/<pid>/node/<nid>/', 'get', view_component, render, {}, {'template_file':'project.html', 'renderer':render_mako_string}),
    ('/project/<pid>/settings/', 'get', project_routes.node_setting, render, {}, {'template_file':'project/settings.html', 'renderer':render_mako_string}),
])

# API

process_urls(app, [

    ('/api/v1/project/<pid>/', 'get', view_project, jsonify, {}, {}),
    ('/api/v1/project/<pid>/get_summary/', 'get', project_routes.get_summary, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/get_summary/', 'get', project_routes.get_summary, jsonify, {}, {}),
    ('/api/v1/project/<pid>/log/', 'get', project_routes.get_logs, jsonify, {}, {}),
    ('/api/v1/project/<pid>/log/<logid>', 'get', project_routes.get_log, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/log/', 'get', project_routes.get_logs, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/log/<logid>', 'get', project_routes.get_log, jsonify, {}, {}),
    # ('/api/v1/log/<logid>/')

    # API keys
    ('/api/v1/project/<pid>/create_key/', 'post', project_routes.create_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/create_key/', 'post', project_routes.create_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/revoke_key/', 'post', project_routes.revoke_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/revoke_key/', 'post', project_routes.revoke_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/keys/', 'get', project_routes.get_node_keys, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/keys/', 'get', project_routes.get_node_keys, jsonify, {}, {}),

    # Reorder components
    ('/api/v1/project/<pid>/reorder_components/', 'post', project_routes.project_reorder_components, jsonify, {}, {}),

    # Edit node
    ('/api/v1/project/<pid>/edit/', 'post', project_routes.edit_node, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/edit/', 'post', project_routes.edit_node, jsonify, {}, {}),

    # Tags
    ('/api/v1/project/<pid>/addtag/<tag>/', 'get', project_routes.project_addtag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/addtag/', 'get', project_routes.project_addtag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/removetag/<tag>/', 'get', project_routes.project_removetag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/removetag/<tag>/', 'get', project_routes.project_removetag, jsonify, {}, {}),

    # Files
    ('/api/v1/project/<pid>/files/upload/', 'get', project_routes.upload_file_get, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/upload/', 'get', project_routes.upload_file_get, jsonify, {}, {}),
    ('/api/v1/project/<pid>/files/upload/', 'post', project_routes.upload_file_public, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/upload/', 'post', project_routes.upload_file_public, jsonify, {}, {}),
    ('/api/v1/project/<pid>/files/delete/<fid>/', 'post', project_routes.delete_file, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/delete/<fid>/', 'post', project_routes.delete_file, jsonify, {}, {}),

    # Add / remove contributors
    ('/api/v1/search/users/', 'post', project_routes.search_user, jsonify, {}, {}),
    ('/api/v1/project/<pid>/addcontributor', 'post', project_routes.project_addcontributor_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/addcontributor', 'post', project_routes.project_addcontributor_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/removecontributors', 'post', project_routes.project_removecontributor, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/removecontributors', 'post', project_routes.project_removecontributor, jsonify, {}, {}),

])