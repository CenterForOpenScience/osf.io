import werkzeug.wrappers
from werkzeug.exceptions import NotFound
import httplib as http

from framework.flask import app, redirect
from framework.mako import makolookup
from mako.template import Template
import framework
from website import settings
from framework import get_current_user

import copy
import json
import os
import pystache
import re
import lxml.html

TEMPLATE_DIR = 'static/templates/'

def nonwrapped_fn(fn, keywords):
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapped

def wrapped_fn(fn, wrapper, fn_kwargs, wrapper_kwargs):
    def wrapped(*args, **kwargs):
        return wrapper(fn(*args, **kwargs), **wrapper_kwargs)
    return wrapped


def call_url(url, wrap=True, view_kwargs=None):

    func_name, func_data = app.url_map.bind('').match(url)
    if view_kwargs is not None:
        func_data.update(view_kwargs)
    view_function = view_functions[func_name]
    ret_val = view_function(**func_data)

    # todo move elsewhere
    if wrap and not isinstance(ret_val, dict):
        if wrap is True:
            wrap = view_function.__name__
            wrap = re.sub('^get_', '', wrap)
        ret_val = {wrap : ret_val}

    return ret_val

view_functions = {}

# todo: add prefix and / or blueprint
# todo: iterable routes, methods
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
            wrapper_name = wrapper.__name__
        else:
            view_func = nonwrapped_fn(fn, fn_kwargs)
            wrapper_name = ''

        view_functions[wrapper_name + '__' + fn.__name__] = fn

        app.add_url_rule(
            url,
            endpoint=wrapper_name + '__' + fn.__name__,
            view_func=view_func,
            methods=[method]
        )

from modularodm import StoredObject
class ODMEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        if isinstance(obj, StoredObject):
            return obj._primary_key
        return json.JSONEncoder.default(self, obj)

class Renderer(object):

    def render(self):
        raise NotImplementedError

    def __call__(self, data, *args, **kwargs):

        # Return if response
        if isinstance(data, werkzeug.wrappers.BaseResponse):
            return data

        # Unpack tuple
        if not isinstance(data, tuple):
            data = (data,)
        data, status_code, headers, resource_uri = data + (None,) * (4 - len(data))

        # Call subclass render
        rendered = self.render(data, resource_uri, *args, **kwargs)

        # Return if response
        if isinstance(data, werkzeug.wrappers.BaseResponse):
            return data

        return rendered, status_code, headers

class JSONRenderer(Renderer):

    __name__ = 'JSONRenderer'

    from modularodm import StoredObject
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, 'to_json'):
                return obj.to_json()
            if isinstance(obj, StoredObject):
                return obj._primary_key
            return json.JSONEncoder.default(self, obj)

    def render(self, data, resource_uri):
        return json.dumps(data, cls=self.Encoder)

class WebRenderer(Renderer):

    __name__ = 'WebRenderer'

    def load_file(self, template_file, template_dir):
        with open(os.path.join(template_dir, template_file), 'r') as f:
            loaded = f.read()
        return loaded

    def render_element(self, element, data, renderer, template_dir):

        element_attributes = element.attrib
        attributes_string = element_attributes['mod-meta']
        element_meta = json.loads(attributes_string) # todo more robust jsonqa

        uri = element_meta.get('uri')
        is_replace = element_meta.get("replace", False)
        kwargs = element_meta.get('kwargs', {})
        view_kwargs = element_meta.get('view_kwargs', {})

        render_data = copy.deepcopy(data)
        render_data.update(kwargs)

        if uri:
            try:
                uri_data = call_url(uri, view_kwargs=view_kwargs)
                render_data.update(uri_data)
            except NotFound:
                return '<div>URI {} not found.</div>'.format(uri), is_replace
            except:
                return '<div>Error retrieving URI {}.</div>'.format(uri), is_replace

        template_rendered = self.render(
            render_data,
            None,
            element_meta['tpl'],
            renderer,
            template_dir=template_dir,
        )

        return template_rendered, is_replace

    def render(self, data, resource_uri, template_name, renderer, template_dir=TEMPLATE_DIR):
        
        if resource_uri is not None:
            return redirect(resource_uri)

        data.update(get_globals())

        template_file = self.load_file(template_name, template_dir)
        rendered = renderer(template_file, data)

        html = lxml.html.fragment_fromstring(rendered, create_parent='remove-me')

        for element in html.findall('.//*[@mod-meta]'):

            template_rendered, is_replace = self.render_element(element, data, renderer, template_dir)

            original = lxml.html.tostring(element)
            if is_replace:
                replacement = template_rendered
            else:
                replacement = lxml.html.tostring(element)
                replacement = replacement.replace('><', '>'+template_rendered+'<')

            rendered = rendered.replace(original, replacement)

        return rendered

# # def render(data, template_file, renderer, build_response=True, template_dir=TEMPLATE_DIR):
# def render(data, template_file, renderer, template_dir=TEMPLATE_DIR):
#
#     # if isinstance(data, werkzeug.wrappers.BaseResponse):
#     #     return data
#     #
#     # if isinstance(data, tuple):
#     #     data, status_code = data
#     # else:
#     #     status_code = 200
#
#     data.update(get_globals())
#
#     rendered = load_file(template_file, template_dir)
#     rendered = renderer(rendered, data)
#
#     html = lxml.html.fragment_fromstring(rendered, create_parent='removeme')
#
#     for el in html.findall('.//*[@mod-meta]'):
#
#         element_attributes = el.attrib
#         attributes_string = element_attributes['mod-meta']
#         element_meta = json.loads(attributes_string) # todo more robust jsonqa
#
#         is_replace = element_meta.get("replace", False)
#
#         render_data = data.copy()
#
#         kwargs = element_meta.get('kwargs', {})
#         view_kwargs = element_meta.get('view_kwargs', {})
#         render_data.update(kwargs)
#
#         uri = element_meta.get('uri')
#         if uri:
#             try:
#                 uri_data = call_url(uri, view_kwargs=view_kwargs)
#                 render_data.update(uri_data)
#                 template_rendered = render(
#                     render_data,
#                     element_meta['tpl'],
#                     renderer,
#                     # build_response=False,
#                     template_dir=template_dir,
#                 )
#             except NotFound:
#                 template_rendered = '<div>URI {} not found.</div>'.format(uri)
#             except:
#                 template_rendered = '<div>Error retrieving URI {}.</div>'.format(uri)
#         else:
#             template_rendered = render(
#                 render_data,
#                 element_meta['tpl'],
#                 renderer,
#                 # build_response=False,
#                 template_dir=template_dir,
#             )
#
#         original = lxml.html.tostring(el)
#         if is_replace:
#             replacement = template_rendered
#         else:
#             replacement = lxml.html.tostring(el)
#             replacement = replacement.replace('><', '>'+template_rendered+'<')
#
#         rendered = rendered.replace(original, replacement)
#
#     # if build_response:
#     #     rendered = make_response((rendered, status_code))
#
#     return rendered

def jsonify(data, label=None):
    if isinstance(data, werkzeug.wrappers.BaseResponse):
        return data
    return json.dumps({label:data} if label else data, cls=ODMEncoder),

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
        'user_name' : user.username if user else '',
        'user_id' : user._primary_key if user else '',
        'display_name' : get_display_name(user.username) if user else '',
        'use_cdn' : settings.use_cdn_for_client_libs,
        'dev_mode' : settings.dev_mode,
        'allow_login' : settings.allow_login,
    }

# def load_file(template_file, template_dir):
#     with open(os.path.join(template_dir, template_file), 'r') as f:
#         loaded = f.read()
#     return loaded

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


from website import views as website_routes
from website.profile import views as profile_views
from website.project import views as project_views

# Base

process_urls(app, [

    ('/dashboard/', 'get', website_routes.dashboard, WebRenderer(), {}, {'template_name' : 'dashboard.html', 'renderer' : render_mako_string}),

])

# Profile

# Web

process_urls(app, [
    ('/profile/', 'get', profile_views.profile_view, WebRenderer(), {}, {'template_name' : 'profile.html', 'renderer' : render_mako_string}),
    ('/profile/<uid>/', 'get', profile_views.profile_view, WebRenderer(), {}, {'template_name' : 'profile.html', 'renderer' : render_mako_string}),
    ('/settings/', 'get', profile_views.profile_settings, WebRenderer(), {}, {'template_name' : 'settings.html', 'renderer' : render_mako_string}),
    ('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, WebRenderer(), {}, {'template_name' : 'profile/key_history.html', 'renderer' : render_mako_string}),
    ('/profile/<uid>/edit/', 'post', profile_views.edit_profile, jsonify, {}, {}),
    ('/addons/', 'get', profile_views.profile_addons, WebRenderer(), {}, {'template_name' : 'profile/addons.html', 'renderer' : render_mako_string}),
])

# API

process_urls(app, [
    ('/api/v1/profile/', 'get', profile_views.profile_view, jsonify, {}, {}),
    ('/api/v1/profile/<uid>/', 'get', profile_views.profile_view, jsonify, {}, {}),
    ('/api/v1/profile/<uid>/public_projects/', 'get', profile_views.get_public_projects, jsonify, {}, {}),
    ('/api/v1/profile/<uid>/public_components/', 'get', profile_views.get_public_components, jsonify, {}, {}),
    ('/api/v1/settings/', 'get', profile_views.profile_settings, jsonify, {}, {}),
    ('/api/v1/settings/keys/', 'get', profile_views.get_keys, jsonify, {}, {}),
    ('/api/v1/settings/create_key/', 'post', profile_views.create_user_key, jsonify, {}, {}),
    ('/api/v1/settings/revoke_key/', 'post', profile_views.revoke_user_key, jsonify, {}, {}),
    ('/api/v1/settings/key_history/<kid>/', 'get', profile_views.user_key_history, jsonify, {}, {}),
])

# Project

# Web

process_urls(app, [
    ('/', 'get', view_index, WebRenderer(), {}, {'template_name':'index.html', 'renderer':render_mako_string}),
    ('/project/<pid>/', 'get', project_views.node.view_project, WebRenderer(), {}, {'template_name':'project.html', 'renderer':render_mako_string}),
    ('/project/<pid>/node/<nid>/', 'get', project_views.node.view_project, WebRenderer(), {}, {'template_name':'project.html', 'renderer':render_mako_string}),
    ('/project/<pid>/settings/', 'get', project_views.node.node_setting, WebRenderer(), {}, {'template_name':'project/settings.html', 'renderer':render_mako_string}),

    ('/project/<pid>/key_history/<kid>/', 'get', project_views.key.node_key_history, WebRenderer(), {}, {'template_name':'project/key_history.html', 'renderer':render_mako_string}),
    ('/project/<pid>/node/<nid>/key_history/<kid>/', 'get', project_views.key.node_key_history, WebRenderer(), {}, {'template_name':'project/key_history.html', 'renderer':render_mako_string}),
    ('/tags/<tag>/', 'get', project_views.tag.project_tag, WebRenderer(), {}, {'template_name' : 'tags.html', 'renderer' : render_mako_string}),

    ('/project/new/', 'get', project_views.node.project_new, WebRenderer(), {}, {'template_name' : 'project/new.html', 'renderer' : render_mako_string}),
    ('/project/new/', 'post', project_views.node.project_new_post, WebRenderer(), {}, {'template_name' : 'project/new.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/newnode/', 'post', project_views.node.project_new_node),#, WebRenderer(), {}, {}),

    ('/project/<pid>/node/<nid>/settings/', 'get', project_views.node.node_setting, WebRenderer(), {}, {'template_name':'project/settings.html', 'renderer':render_mako_string}),

    ### Files ###
    ('/project/<pid>/files/', 'get', project_views.file.list_files, WebRenderer(), {}, {'template_name':'project/files.html', 'renderer':render_mako_string}),
    ('/project/<pid>/node/<nid>/files/', 'get', project_views.file.list_files, WebRenderer(), {}, {'template_name':'project/files.html', 'renderer':render_mako_string}),

    ('/project/<pid>/files/<fid>/', 'get', project_views.file.view_file, WebRenderer(), {}, {'template_name' : 'project/file.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/files/<fid>/', 'get', project_views.file.view_file, WebRenderer(), {}, {'template_name' : 'project/file.html', 'renderer' : render_mako_string}),

    # # Forks
    # ('/project/<pid>/fork/', 'post', project_views.node_fork_page, WebRenderer(), {}, {}),
    # ('/project/<pid>/node/<nid>/fork/', 'post', project_views.node_fork_page, WebRenderer(), {}, {}),

    # View forks
    ('/project/<pid>/forks/', 'get', project_views.node.node_forks, WebRenderer(), {}, {'template_name' : 'project/forks.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/forks/', 'get', project_views.node.node_forks, WebRenderer(), {}, {'template_name' : 'project/forks.html', 'renderer' : render_mako_string}),

    # Registrations
    ('/project/<pid>/register/', 'get', project_views.register.node_register_page, WebRenderer(), {}, {'template_name' : 'project/register.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/register/', 'get', project_views.register.node_register_page, WebRenderer(), {}, {'template_name' : 'project/register.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/register/<template>/', 'get', project_views.register.node_register_template_page, WebRenderer(), {}, {'template_name' : 'project/register.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/register/<template>/', 'get', project_views.register.node_register_template_page, WebRenderer(), {}, {'template_name' : 'project/register.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/registrations/', 'get', project_views.node.node_registrations, WebRenderer(), {}, {'template_name' : 'project/registrations.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/registrations/', 'get', project_views.node.node_registrations, WebRenderer(), {}, {'template_name' : 'project/registrations.html', 'renderer' : render_mako_string}),

    # Statistics
    ('/project/<pid>/statistics/', 'get', project_views.node.project_statistics, WebRenderer(), {}, {'template_name' : 'project/statistics.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/statistics/', 'get', project_views.node.project_statistics, WebRenderer(), {}, {'template_name' : 'project/statistics.html', 'renderer' : render_mako_string}),

    ### Wiki ###
    ('/project/<pid>/wiki/', 'get', project_views.wiki.project_project_wikimain),
    ('/project/<pid>/node/<nid>/wiki/', 'get', project_views.wiki.project_node_wikihome),

    # View
    ('/project/<pid>/wiki/<wid>/', 'get', project_views.wiki.project_wiki_page, WebRenderer(), {}, {'template_name' : 'project/wiki.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/wiki/<wid>/', 'get', project_views.wiki.project_wiki_page, WebRenderer(), {}, {'template_name' : 'project/wiki.html', 'renderer' : render_mako_string}),

    # Edit | GET
    ('/project/<pid>/wiki/<wid>/edit/', 'get', project_views.wiki.project_wiki_edit, WebRenderer(), {}, {'template_name' : 'project/wiki/edit.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/wiki/<wid>/edit/', 'get', project_views.wiki.project_wiki_edit, WebRenderer(), {}, {'template_name' : 'project/wiki/edit.html', 'renderer' : render_mako_string}),

    # Compare
    ('/project/<pid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_compare, WebRenderer(), {}, {'template_name' : 'project/wiki/compare.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_compare, WebRenderer(), {}, {'template_name' : 'project/wiki/compare.html', 'renderer' : render_mako_string}),

    # Versions
    ('/project/<pid>/wiki/<wid>/version/<vid>/', 'get', project_views.wiki.project_wiki_version, WebRenderer(), {}, {'template_name' : 'project/wiki/compare.html', 'renderer' : render_mako_string}),
    ('/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/', 'get', project_views.wiki.project_wiki_version, WebRenderer(), {}, {'template_name' : 'project/wiki/compare.html', 'renderer' : render_mako_string}),

])

# API

class Rule(object):

    @staticmethod
    def _to_list(value):
        if not isinstance(value, list):
            return [value]
        return value

    def __init__(self, routes, methods, view_func, render_func=None, view_kwargs=None, render_kwargs=None):
        self.routes = self._to_list(routes)
        self.methods = self._to_list(methods)
        self.view_func = view_func
        self.render_func = render_func
        self.view_kwargs = view_kwargs or {}
        self.render_kwargs = render_kwargs or {}

process_urls(app, [

    ('/api/v1/tags/<tag>/', 'get', project_views.tag.project_tag, jsonify, {}, {}),

    ('/api/v1/project/<pid>/', 'get', project_views.node.view_project, jsonify, {}, {}),
    ('/api/v1/project/<pid>/get_summary/', 'get', project_views.node.get_summary, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/get_summary/', 'get', project_views.node.get_summary, jsonify, {}, {}),
    ('/api/v1/project/<pid>/log/', 'get', project_views.log.get_logs, jsonify, {}, {}),
    ('/api/v1/log/<log_id>/', 'get', project_views.log.get_log, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/log/', 'get', project_views.log.get_logs, jsonify, {}, {}),

    ('/api/v1/project/<pid>/get_contributors/', 'get', project_views.contributor.get_contributors, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/get_contributors/', 'get', project_views.contributor.get_contributors, jsonify, {}, {}),

    # Create
    ('/api/v1/project/new/', 'post', project_views.node.project_new_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/newnode/', 'post', project_views.node.project_new_node, jsonify, {}, {}),

    # Remove
    ('/api/v1/project/<pid>/remove/', 'post', project_views.node.component_remove, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/remove/', 'post', project_views.node.component_remove, jsonify, {}, {}),

    # API keys
    ('/api/v1/project/<pid>/create_key/', 'post', project_views.key.create_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/create_key/', 'post', project_views.key.create_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/revoke_key/', 'post', project_views.key.revoke_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/revoke_key/', 'post', project_views.key.revoke_node_key, jsonify, {}, {}),
    ('/api/v1/project/<pid>/keys/', 'get', project_views.key.get_node_keys, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/keys/', 'get', project_views.key.get_node_keys, jsonify, {}, {}),

    # Reorder components
    ('/api/v1/project/<pid>/reorder_components/', 'post', project_views.node.project_reorder_components, jsonify, {}, {}),

    # Edit node
    ('/api/v1/project/<pid>/edit/', 'post', project_views.node.edit_node, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/edit/', 'post', project_views.node.edit_node, jsonify, {}, {}),

    # Tags
    ('/api/v1/project/<pid>/addtag/<tag>/', 'get', project_views.tag.project_addtag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/addtag/', 'get', project_views.tag.project_addtag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/removetag/<tag>/', 'get', project_views.tag.project_removetag, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/removetag/<tag>/', 'get', project_views.tag.project_removetag, jsonify, {}, {}),

    ### Files ###
    ('/api/v1/project/<pid>/files/', 'get', project_views.file.list_files, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/', 'get', project_views.file.list_files, jsonify, {}, {}),

    ('/api/v1/project/<pid>/get_files/', 'get', project_views.file.get_files, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/get_files/', 'get', project_views.file.get_files, jsonify, {}, {}),

    ('/api/v1/project/<pid>/files/upload/', 'get', project_views.file.upload_file_get, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/upload/', 'get', project_views.file.upload_file_get, jsonify, {}, {}),
    ('/api/v1/project/<pid>/files/upload/', 'post', project_views.file.upload_file_public, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/upload/', 'post', project_views.file.upload_file_public, jsonify, {}, {}),
    ('/api/v1/project/<pid>/files/delete/<fid>/', 'post', project_views.file.delete_file, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/files/delete/<fid>/', 'post', project_views.file.delete_file, jsonify, {}, {}),

    # Add / remove contributors
    ('/api/v1/search/users/', 'post', project_views.node.search_user, jsonify, {}, {}),
    ('/api/v1/project/<pid>/addcontributor/', 'post', project_views.contributor.project_addcontributor_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/addcontributor/', 'post', project_views.contributor.project_addcontributor_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/removecontributors/', 'post', project_views.contributor.project_removecontributor, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/removecontributors/', 'post', project_views.contributor.project_removecontributor, jsonify, {}, {}),

    # Forks
    ('/api/v1/project/<pid>/fork/', 'post', project_views.node.node_fork_page),#, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/fork/', 'post', project_views.node.node_fork_page),#, jsonify, {}, {}),

    # View forks
    ('/api/v1/project/<pid>/forks/', 'get', project_views.node.node_forks, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/forks/', 'get', project_views.node.node_forks, jsonify, {}, {}),

    # Registrations
    ('/api/v1/project/<pid>/register/<template>/', 'get', project_views.register.node_register_template_page, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/register/<template>/', 'get', project_views.register.node_register_template_page, jsonify, {}, {}),

    ('/api/v1/project/<pid>/register/<template>/', 'post', project_views.register.node_register_template_page_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/register/<template>/', 'post', project_views.register.node_register_template_page_post, jsonify, {}, {}),

    # Statistics
    ('/api/v1/project/<pid>/statistics/', 'get', project_views.node.project_statistics, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/statistics/', 'get', project_views.node.project_statistics, jsonify, {}, {}),

    # Permissions
    ('/api/v1/project/<pid>/permissions/<permissions>/', 'get', project_views.node.project_set_permissions, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/permissions/<permissions>/', 'get', project_views.node.project_set_permissions, jsonify, {}, {}),


    ### Wiki ###

    # View
    ('/api/v1/project/<pid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_page, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_page, jsonify, {}, {}),

    # Edit | POST
    ('/api/v1/project/<pid>/wiki/<wid>/edit/', 'post', project_views.wiki.project_wiki_edit_post, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/wiki/<wid>/edit/', 'post', project_views.wiki.project_wiki_edit_post, jsonify, {}, {}),

    # Compare
    ('/api/v1/project/<pid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_compare, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/', 'get', project_views.wiki.project_wiki_compare, jsonify, {}, {}),

    # Versions
    ('/api/v1/project/<pid>/wiki/<wid>/version/<vid>/', 'get', project_views.wiki.project_wiki_version, jsonify, {}, {}),
    ('/api/v1/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/', 'get', project_views.wiki.project_wiki_version, jsonify, {}, {}),

])