import werkzeug.wrappers
from werkzeug.exceptions import NotFound
from framework import StoredObject

from framework import HTTPError
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

# todo fix this
def nonwrapped_fn(fn, keywords):
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapped


def decorator(fn):
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapped

from framework import session

def wrapped_fn(fn, wrapper, fn_kwargs):
    def wrapped(*args, **kwargs):
        try:
            session_error_code = session.get('auth_error_code')
            if session_error_code:
                raise HTTPError(session_error_code)
            rv = fn(*args, **kwargs)
        except HTTPError as error:
            rv = error
        return wrapper(rv, **fn_kwargs)
    return wrapped


def call_url(url, wrap=True, view_kwargs=None):

    # Parse view function and args
    func_name, func_data = app.url_map.bind('').match(url)
    if view_kwargs is not None:
        func_data.update(view_kwargs)
    view_function = view_functions[func_name]

    # Call view function
    rv = view_function(**func_data)

    # Follow redirects
    if isinstance(rv, werkzeug.wrappers.BaseResponse) \
            and rv.status_code in [302, 303]:
        url_redirect = rv.headers['Location']
        return call_url(url_redirect, wrap=wrap)

    # TODO: move elsewhere
    if wrap and not isinstance(rv, dict):
        if wrap is True:
            wrap = view_function.__name__
            wrap = re.sub('^get_', '', wrap)
        rv = {wrap : rv}

    return rv

view_functions = {}

def process_rules(app, rules, prefix=''):

    for rule in rules:

        if rule.render_func:
            view_func = wrapped_fn(rule.view_func, rule.render_func, rule.view_kwargs)
            wrapper_name = rule.render_func.__name__
        else:
            view_func = nonwrapped_fn(rule.view_func, rule.view_kwargs)
            wrapper_name = ''

        view_functions[wrapper_name + '__' + rule.view_func.__name__] = rule.view_func

        for url in rule.routes:
            app.add_url_rule(
                prefix + url,
                endpoint=wrapper_name + '__' + rule.view_func.__name__,
                view_func=view_func,
                methods=rule.methods
            )

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


class Renderer(object):

    def render(self, data, resource_uri, *args, **kwargs):
        raise NotImplementedError

    def handle_error(self, error):
        raise NotImplementedError

    def __call__(self, data, *args, **kwargs):

        # Handle error
        if isinstance(data, HTTPError):
            return self.handle_error(data)

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
        if isinstance(rendered, werkzeug.wrappers.BaseResponse):
            return rendered

        return rendered, status_code, headers


class JSONRenderer(Renderer):
    """
    Renderer for API views. Generates JSON; ignores
    redirects from views and exceptions.
    """

    __name__ = 'JSONRenderer'

    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, 'to_json'):
                return obj.to_json()
            if isinstance(obj, StoredObject):
                return obj._primary_key
            return json.JSONEncoder.default(self, obj)

    def handle_error(self, error):
        return self.render(error.to_data(), None), error.code

    def render(self, data, resource_uri, *args, **kwargs):
        return json.dumps(data, cls=self.Encoder)

class WebRenderer(Renderer):
    """
    Renderer for web views. Generates HTML; follows redirects
    from views and exceptions.
    """

    __name__ = 'WebRenderer'
    error_template = 'error.html'

    def __init__(self, template_name, renderer, template_dir=TEMPLATE_DIR):
        self.template_name = template_name
        self.renderer = renderer
        self.template_dir = template_dir

    def handle_error(self, error):

        if error.resource_uri is not None:
            return redirect(error.resource_uri)

        error_data = error.to_data()
        return self._render(
            error_data,
            self.error_template
        ), error.code

    def load_file(self, template_file):
        with open(os.path.join(self.template_dir, template_file), 'r') as f:
            loaded = f.read()
        return loaded

    def render_element(self, element, data):

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

        template_rendered = self._render(
            render_data,
            element_meta['tpl'],
        )

        return template_rendered, is_replace

    def _render(self, data, template_name=None):

        data.update(get_globals())

        template_name = template_name or self.template_name
        template_file = self.load_file(template_name)
        rendered = self.renderer(template_file, data)

        html = lxml.html.fragment_fromstring(rendered, create_parent='remove-me')

        for element in html.findall('.//*[@mod-meta]'):

            template_rendered, is_replace = self.render_element(element, data)

            original = lxml.html.tostring(element)
            if is_replace:
                replacement = template_rendered
            else:
                replacement = lxml.html.tostring(element)
                replacement = replacement.replace('><', '>'+template_rendered+'<')

            rendered = rendered.replace(original, replacement)

        return rendered

    def render(self, data, resource_uri, *args, **kwargs):
        if resource_uri is not None:
            return redirect(resource_uri)
        template_name = kwargs.get('template_name')
        return self._render(data, template_name)

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
        'status' : framework.status.pop_status_messages(),
    }

def view_index():

    display_name = username = framework.get_current_username()
    if username and len(username) > 22:
        display_name = get_display_name(username)

    return {
        'user_name': username,
        'display_name': display_name,
        'status': framework.status.pop_status_messages(),
    }


from website import views as website_routes
from website.profile import views as profile_views
from website.project import views as project_views

class Rule(object):

    @staticmethod
    def _to_list(value):
        if not isinstance(value, list):
            return [value]
        return value

    def __init__(self, routes, methods, view_func, render_func=None, view_kwargs=None):
        self.routes = self._to_list(routes)
        self.methods = self._to_list(methods)
        self.view_func = view_func
        self.render_func = render_func
        self.view_kwargs = view_kwargs or {}

# Base

process_rules(app, [

    Rule('/dashboard/', 'get', website_routes.dashboard, WebRenderer('dashboard.html', render_mako_string)),

])

# Profile

# Web

process_rules(app, [

    Rule('/profile/', 'get', profile_views.profile_view, WebRenderer('profile.html', render_mako_string)),
    Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, WebRenderer('profile.html', render_mako_string)),
    Rule('/settings/', 'get', profile_views.profile_settings, WebRenderer('settings.html', render_mako_string)),
    Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, WebRenderer('profile/key_history.html', render_mako_string)),
    Rule('/profile/<uid>/edit', 'post', profile_views.edit_profile, JSONRenderer),
    Rule('/addons/', 'get', profile_views.profile_addons, WebRenderer('profile/addons.html', render_mako_string)),

])

# API

process_rules(app, [

    Rule('/profile/', 'get', profile_views.profile_view, JSONRenderer()),
    Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, JSONRenderer()),
    Rule('/profile/<uid>/public_projects/', 'get', profile_views.get_public_projects, JSONRenderer()),
    Rule('/profile/<uid>/public_components/', 'get', profile_views.get_public_components, JSONRenderer()),
    Rule('/settings/', 'get', profile_views.profile_settings, JSONRenderer()),
    Rule('/settings/keys/', 'get', profile_views.get_keys, JSONRenderer()),
    Rule('/settings/create_key/', 'post', profile_views.create_user_key, JSONRenderer()),
    Rule('/settings/revoke_key/', 'post', profile_views.revoke_user_key, JSONRenderer()),
    Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, JSONRenderer()),

], prefix='/api/v1',)

# Project

# Web

process_rules(app, [

    Rule('/', 'get', view_index, WebRenderer('index.html', render_mako_string)),

    Rule([
        '/project/<pid>/',
        '/project/<pid>/node/<nid>/',
    ], 'get', project_views.node.view_project, WebRenderer('project.html', render_mako_string)),

    Rule([
        '/project/<pid>/key_history/<kid>/',
        '/project/<pid>/node/<nid>/key_history/<kid>/',
    ], 'get', project_views.key.node_key_history, WebRenderer('project/key_history.html', render_mako_string)),

    Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, WebRenderer('tags.html', render_mako_string)),

    Rule('/project/new/', 'get', project_views.node.project_new, WebRenderer('project/new.html', render_mako_string)),
    Rule('/project/new/', 'post', project_views.node.project_new_post, WebRenderer('project/new.html', render_mako_string)),

    Rule('/project/<pid>/newnode/', 'post', project_views.node.project_new_node, WebRenderer('project.html', render_mako_string)),

    Rule([
        '/project/<pid>/settings/',
        '/project/<pid>/node/<nid>/settings/',
    ], 'get', project_views.node.node_setting, WebRenderer('project/settings.html', render_mako_string)),

    # Permissions
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/permissions/<permissions>/',
        '/project/<pid>/node/<nid>/permissions/<permissions>/',
    ], 'get', project_views.node.project_set_permissions, WebRenderer('project.html', render_mako_string)),

    ### Files ###

    Rule([
        '/project/<pid>/files/',
        '/project/<pid>/node/<nid>/files/',
    ], 'get', project_views.file.list_files, WebRenderer('project/files.html', render_mako_string)),

    Rule([
        '/project/<pid>/files/<fid>/',
        '/project/<pid>/node/<nid>/files/<fid>/',
    ], 'get', project_views.file.view_file, WebRenderer('project/file.html', render_mako_string)),

    # View forks
    Rule([
        '/project/<pid>/forks/',
        '/project/<pid>/node/<nid>/forks/',
    ], 'get', project_views.node.node_forks, WebRenderer('project/forks.html', render_mako_string)),

    # Registrations
    Rule([
        '/project/<pid>/register/',
        '/project/<pid>/node/<nid>/register/',
    ], 'get', project_views.register.node_register_page, WebRenderer('project/register.html', render_mako_string)),

    Rule([
        '/project/<pid>/register/<template>/',
        '/project/<pid>/node/<nid>/register/<template>/',
    ], 'get', project_views.register.node_register_template_page, WebRenderer('project/register.html', render_mako_string)),

    Rule([
        '/project/<pid>/registrations/',
        '/project/<pid>/node/<nid>/registrations/',
    ], 'get', project_views.node.node_registrations, WebRenderer('project/registrations.html', render_mako_string)),

    # Statistics
    Rule([
        '/project/<pid>/statistics/',
        '/project/<pid>/node/<nid>/statistics/',
    ], 'get', project_views.node.project_statistics, WebRenderer('project/statistics.html', render_mako_string)),

    ### Wiki ###
    Rule([
        '/project/<pid>/wiki/',
        '/project/<pid>/node/<nid>/wiki/',
    ], 'get', project_views.wiki.project_wiki_home, WebRenderer('project/wiki.html', render_mako_string)),

    # View
    Rule([
        '/project/<pid>/wiki/<wid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/',
    ], 'get', project_views.wiki.project_wiki_page, WebRenderer('project/wiki.html', render_mako_string)),

    # Edit | GET
    Rule([
        '/project/<pid>/wiki/<wid>/edit/',
        '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
    ], 'get', project_views.wiki.project_wiki_edit, WebRenderer('project/wiki/edit.html', render_mako_string)),

    # Edit | POST
    Rule([
        '/project/<pid>/wiki/<wid>/edit/',
        '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
    ], 'post', project_views.wiki.project_wiki_edit_post, WebRenderer('project/wiki/edit.html', render_mako_string)),

    # Compare
    Rule([
        '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
    ], 'get', project_views.wiki.project_wiki_compare, WebRenderer('project/wiki/compare.html', render_mako_string)),

    # Versions
    Rule([
        '/project/<pid>/wiki/<wid>/version/<vid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
    ], 'get', project_views.wiki.project_wiki_version, WebRenderer('project/wiki/compare.html', render_mako_string)),

])

# API

process_rules(app, [

    Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, JSONRenderer()),

    Rule('/project/<pid>/', 'get', project_views.node.view_project, JSONRenderer()),

    Rule([
        '/project/<pid>/get_summary/',
        '/project/<pid>/node/<nid>/get_summary/',
    ], 'get', project_views.node.get_summary, json),

    Rule([
        '/project/<pid>/get_children/',
        '/project/<pid>/node/<nid>/get_children/',
    ], 'get', project_views.node.get_children, JSONRenderer()),

    Rule('/log/<log_id>/', 'get', project_views.log.get_log, JSONRenderer()),
    Rule([
        '/project/<pid>/log/',
        '/project/<pid>/node/<nid>/log/',
    ], 'get', project_views.log.get_logs, JSONRenderer()),

    Rule([
        '/project/<pid>/get_contributors/',
        '/project/<pid>/node/<nid>/get_contributors/',
    ], 'get', project_views.contributor.get_contributors, JSONRenderer()),

    # Create
    Rule([
        '/project/new/',
        '/project/<pid>/newnode/',
    ], 'post', project_views.node.project_new_post, JSONRenderer()),

    # Remove
    Rule([
        '/project/<pid>/remove/',
        '/project/<pid>/node/<nid>/remove/',
    ], 'post', project_views.node.component_remove, JSONRenderer()),

    # API keys
    Rule([
        '/project/<pid>/create_key/',
        '/project/<pid>/node/<nid>/create_key/',
    ], 'post', project_views.key.create_node_key, JSONRenderer()),
    Rule([
        '/project/<pid>/revoke_key/',
        '/project/<pid>/node/<nid>/revoke_key/'
    ], 'post', project_views.key.revoke_node_key,  JSONRenderer()),
    Rule([
        '/project/<pid>/keys/',
        '/project/<pid>/node/<nid>/keys/',
    ], 'get', project_views.key.get_node_keys, JSONRenderer()),

    # Reorder components
    Rule('/project/<pid>/reorder_components/', 'post', project_views.node.project_reorder_components, JSONRenderer()),

    # Edit node
    Rule([
        '/project/<pid>/edit/',
        '/project/<pid>/node/<nid>/edit/',
    ], 'post', project_views.node.edit_node, JSONRenderer()),

    # Tags
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/addtag/<tag>/',
        '/project/<pid>/node/<nid>/addtag/<tag>/',
    ], 'get', project_views.tag.project_addtag, JSONRenderer()),
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/removetag/<tag>/',
        '/project/<pid>/node/<nid>/removetag/<tag>/',
    ], 'get', project_views.tag.project_removetag, JSONRenderer()),

    ### Files ###
    Rule([
        '/project/<pid>/files/',
        '/project/<pid>/node/<nid>/files/',
    ], 'get', project_views.file.list_files, JSONRenderer()),

    Rule([
        '/project/<pid>/get_files/',
        '/project/<pid>/node/<nid>/get_files/',
    ], 'get', project_views.file.get_files, JSONRenderer()),

    # Download file
    Rule([
        '/project/<pid>/files/download/<fid>/',
        '/project/<pid>/node/<nid>/files/download/<fid>/',
    ], 'get', project_views.file.download_file, JSONRenderer()),

    # Download file by version
    Rule([
        '/project/<pid>/files/download/<fid>/version/<vid>/',
        '/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',
    ], 'get', project_views.file.download_file_by_version, JSONRenderer()),

    Rule([
        '/project/<pid>/files/upload/',
        '/project/<pid>/node/<nid>/files/upload/',
    ], 'get', project_views.file.upload_file_get, JSONRenderer()),
    Rule([
        '/project/<pid>/files/upload/',
        '/project/<pid>/node/<nid>/files/upload/',
    ], 'post', project_views.file.upload_file_public, JSONRenderer()),
    Rule([
        '/project/<pid>/files/delete/<fid>/',
        '/project/<pid>/node/<nid>/files/delete/<fid>/',
    ], 'post', project_views.file.delete_file, JSONRenderer()),

    # Add / remove contributors
    Rule('/search/users/', 'post', project_views.node.search_user, JSONRenderer()),
    Rule([
        '/project/<pid>/addcontributor/',
        '/project/<pid>/node/<nid>/addcontributor/',
    ], 'post', project_views.contributor.project_addcontributor_post, JSONRenderer()),
    Rule([
        '/project/<pid>/removecontributors/',
        '/project/<pid>/node/<nid>/removecontributors/',
    ], 'post', project_views.contributor.project_removecontributor, JSONRenderer()),

    # Forks
    Rule([
        '/project/<pid>/fork/',
        '/project/<pid>/node/<nid>/fork/',
    ], 'post', project_views.node.node_fork_page),

    # View forks
    Rule([
        '/project/<pid>/forks/',
        '/project/<pid>/node/<nid>/forks/',
    ], 'get', project_views.node.node_forks, JSONRenderer()),

    # Registrations
    Rule([
        '/project/<pid>/register/<template>/',
        '/project/<pid>/node/<nid>/register/<template>/',
    ], 'get', project_views.register.node_register_template_page, JSONRenderer()),

    Rule([
        '/project/<pid>/register/<template>/',
        '/project/<pid>/node/<nid>/register/<template>/',
    ], 'post', project_views.register.node_register_template_page_post, JSONRenderer()),

    # Statistics
    Rule([
        '/project/<pid>/statistics/',
        '/project/<pid>/node/<nid>/statistics/',
    ], 'get', project_views.node.project_statistics, JSONRenderer()),

    # Permissions
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/permissions/<permissions>/',
        '/project/<pid>/node/<nid>/permissions/<permissions>/',
    ], 'get', project_views.node.project_set_permissions, JSONRenderer()),


    ### Wiki ###

    # View
    Rule([
        '/project/<pid>/wiki/<wid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/',
    ], 'get', project_views.wiki.project_wiki_page, JSONRenderer()),

    # Edit | POST
    Rule([
        '/project/<pid>/wiki/<wid>/edit/',
        '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
    ], 'post', project_views.wiki.project_wiki_edit_post, JSONRenderer()),

    # Compare
    Rule([
        '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
    ], 'get', project_views.wiki.project_wiki_compare, JSONRenderer()),

    # Versions
    Rule([
        '/project/<pid>/wiki/<wid>/version/<vid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
    ], 'get', project_views.wiki.project_wiki_version, JSONRenderer()),

], prefix='/api/v1')