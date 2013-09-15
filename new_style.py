from framework.flask import app, request, make_response
from framework.mako import makolookup
from mako.template import Template
import framework
from website.models import Node

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

        app.add_url_rule(
            url,
            endpoint=wrapper.__name__ + fn.__name__,
            view_func=view_func,
            methods=[method]
        )

def jsonify(data):
    return app.response_class(
        json.dumps(data),
        mimetype='application/json'
    )

def render(data, template_file, renderer):
    rendered = load_file(template_file)
    html = lxml.html.fragment_fromstring(rendered, create_parent='removeme')

    for el in html.findall('.//*[@mod-meta]'):
        element_attributes = el.attrib
        attributes_string = element_attributes['mod-meta']
        element_meta = json.loads(attributes_string) # todo more robust jsonqa
        template_rendered = load_file(element_meta["tpl"])
        is_replace = element_meta.get("replace", False)

        original = lxml.html.tostring(el)
        if is_replace:
            replacement = template_rendered
        else:
            replacement = lxml.html.tostring(el)
            replacement = replacement.replace('><', '>'+template_rendered+'<')

        rendered = rendered.replace(original, replacement)

    return renderer(rendered, data)

def load_file(template_file):
    with open(os.path.join('static/templates/', template_file), 'r') as f:
        loaded = f.read()
    return loaded

def render_mustache_string(tpl_string, data):
    return pystache.render(tpl_string, context=data)

def render_jinja_string(tpl, data):
    pass

def render_mako_string(tpl, data):
    return Template(tpl, lookup=makolookup).render(**data)

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
        'project':project,
        'user':user,
        'node_to_use': project,
    }

process_urls(app, [
    ('/', 'get', view_index, render, {}, {'template_file':'index.html', 'renderer':render_mako_string}),
    ('/project/<pid>/', 'get', view_project, render, {}, {'template_file':'project.html', 'renderer':render_mako_string}),
])