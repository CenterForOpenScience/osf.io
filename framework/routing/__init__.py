# -*- coding: utf-8 -*-
import werkzeug.wrappers
from werkzeug.exceptions import NotFound
from framework import StoredObject

from framework import HTTPError
from framework.flask import app, redirect, make_response
from framework.mako import makolookup
from mako.template import Template

from framework import session

import os
import copy
import json
import pystache
import lxml.html
import httplib as http

TEMPLATE_DIR = 'static/templates/'
REDIRECT_CODES = [
    http.MOVED_PERMANENTLY,
    http.FOUND,
]

class Rule(object):
    """ Container for routing and rendering rules."""

    @staticmethod
    def _ensure_list(value):
        if not isinstance(value, list):
            return [value]
        return value

    @staticmethod
    def _ensure_slash(value):
        if not value.endswith('/'):
            return value + '/'
        return value

    def __init__(self, routes, methods, view_func_or_data, renderer,
                 view_kwargs=None, endpoint_suffix=''):
        """Rule constructor.

        :param routes: Route or list of routes
        :param methods: HTTP method or list of methods
        :param view_func_or_data: View function or data; pass data
            if view returns a constant data dictionary
        :param renderer: Renderer object or function
        :param view_kwargs: Optional kwargs to pass to view function
        :param endpoint_suffix: Optional suffix to append to endpoint name;
            useful for disambiguating routes by HTTP verb

        """
        if not callable(renderer):
            raise ValueError('Argument renderer must be callable.')
        self.routes = [
            self._ensure_slash(route)
            for route in self._ensure_list(routes)
        ]
        self.methods = self._ensure_list(methods)
        self.view_func_or_data = view_func_or_data
        self.renderer = renderer
        self.view_kwargs = view_kwargs or {}
        self.endpoint_suffix = endpoint_suffix


def wrap_with_renderer(fn, renderer, renderer_kwargs=None, debug_mode=True):
    """

    :param fn: View function; must return a dictionary or a tuple containing
        (up to) a dictionary, status code, headers, and redirect URL
    :param renderer: Renderer object or function
    :param renderer_kwargs: Optional kwargs to pass to renderer
    :return: Wrapped view function

    """
    def wrapped(*args, **kwargs):
        try:
            session_error_code = session.data.get('auth_error_code')
            if session_error_code:
                raise HTTPError(session_error_code)
            rv = fn(*args, **kwargs)
        except HTTPError as error:
            rv = error
        except Exception as error:
            if debug_mode:
                raise error
            rv = HTTPError(
                http.INTERNAL_SERVER_ERROR,
                message=repr(error),
            )
        return renderer(rv, **renderer_kwargs or {})
    return wrapped


view_functions = {}

def data_to_lambda(data):
    return lambda *args, **kwargs: data

def process_rules(app, rules, prefix=''):
    """Add URL routes to Flask / Werkzeug lookup table.

    :param app: Flask / Werkzeug app
    :param rules: List of Rule objects
    :param prefix: Optional prefix for rule URLs

    """
    for rule in rules:

        if callable(rule.view_func_or_data):

            view_func = rule.view_func_or_data
            renderer_name = getattr(
                rule.renderer,
                '__name__',
                rule.renderer.__class__.__name__
            )
            endpoint = '{}__{}'.format(
                renderer_name,
                rule.view_func_or_data.__name__
            )
            view_functions[endpoint] = rule.view_func_or_data

        else:

            view_func = data_to_lambda(rule.view_func_or_data)
            endpoint = '__'.join(
                route.replace('/', '') for route in rule.routes
            )

        wrapped_view_func = wrap_with_renderer(
            view_func,
            rule.renderer,
            rule.view_kwargs,
            debug_mode=app.debug
        )

        for url in rule.routes:
            app.add_url_rule(
                prefix + url,
                endpoint=endpoint + rule.endpoint_suffix,
                view_func=wrapped_view_func,
                methods=rule.methods,
            )


### Renderer helpers ###

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

renderer_extension_map = {
    '.stache': render_mustache_string,
    '.jinja': render_jinja_string,
    '.mako': render_mako_string,
}

def unpack(data, n=4):
    """Unpack data to tuple of length n.

    :param data: Object or tuple of length <= n
    :param n: Length to pad tuple

    """
    if not isinstance(data, tuple):
        data = (data,)
    return data + (None,) * (n - len(data))

def call_url(url, view_kwargs=None):
    """Look up and call view function by URL.

    :param url: URL
    :param view_kwargs: Optional kwargs to pass to view function
    :return: Data from view function

    """
    # Parse view function and args
    func_name, func_data = app.url_map.bind('').match(url)
    if view_kwargs is not None:
        func_data.update(view_kwargs)
    view_function = view_functions[func_name]

    # Call view function
    rv = view_function(**func_data)

    # Extract data from return value
    rv, _, _, _ = unpack(rv)

    # Follow redirects
    if isinstance(rv, werkzeug.wrappers.BaseResponse) \
            and rv.status_code in REDIRECT_CODES:
        redirect_url = rv.headers['Location']
        return call_url(redirect_url)

    return rv

### Renderers ###

class Renderer(object):

    CONTENT_TYPE = "text/html"

    def render(self, data, redirect_url, *args, **kwargs):
        raise NotImplementedError

    def handle_error(self, error):
        raise NotImplementedError

    def __call__(self, data, *args, **kwargs):
        """Render data returned by a view function.

        :param data: Dictionary or tuple of (up to) dictionary,
            status code, headers, and redirect URL
        :return: Flask / Werkzeug response object

        """
        # Handle error
        if isinstance(data, HTTPError):
            return self.handle_error(data)

        # Return if response
        if isinstance(data, werkzeug.wrappers.BaseResponse):
            return data

        # Unpack tuple
        data, status_code, headers, redirect_url = unpack(data)

        # Call subclass render
        rendered = self.render(data, redirect_url, *args, **kwargs)

        # Return if response
        if isinstance(rendered, werkzeug.wrappers.BaseResponse):
            return rendered

        # Set content type in headers
        headers = headers or {}
        headers["Content-Type"] = self.CONTENT_TYPE + "; charset=" + kwargs.get("charset", "utf-8")

        # Package as response
        return make_response(rendered, status_code, headers)


class JSONRenderer(Renderer):
    """Renderer for API views. Generates JSON; ignores
    redirects from views and exceptions.

    """

    CONTENT_TYPE = "application/json"

    # todo: remove once storedobjects are no longer passed from view functions
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, 'to_json'):
                return obj.to_json()
            if isinstance(obj, StoredObject):
                return obj._primary_key
            return json.JSONEncoder.default(self, obj)

    def handle_error(self, error):
        return self.render(error.to_data(), None), error.code

    def render(self, data, redirect_url, *args, **kwargs):
        return json.dumps(data, cls=self.Encoder)

# Create a single JSONRenderer instance to avoid repeated construction
json_renderer = JSONRenderer()

class WebRenderer(Renderer):
    """Renderer for web views. Generates HTML; follows redirects
    from views and exceptions.

    """

    CONTENT_TYPE = "text/html"
    error_template = 'error.mako'

    def detect_renderer(self, renderer, filename):

        if renderer:
            return renderer

        try:
            _, extension = os.path.splitext(filename)
            return renderer_extension_map[extension]
        except KeyError:
            raise Exception(
                'Could not infer renderer from file name: {}'.format(
                    filename
                )
            )

    def __init__(self, template_name, renderer=None, error_renderer=None,
                 data=None, template_dir=TEMPLATE_DIR):
        """Construct WebRenderer.

        :param template_name: Name of template file
        :param renderer: Renderer callable; attempt to auto-detect if None
        :param error_renderer: Renderer for error views; attempt to
            auto-detect if None
        :param data: Optional dictionary or dictionary-generating function
                     to add to data from view function
        :param template_dir: Path to template directory

        """
        self.template_name = template_name
        self.data = data or {}
        self.template_dir = template_dir


        self.renderer = self.detect_renderer(renderer, template_name)
        self.error_renderer = self.detect_renderer(
            error_renderer,
            self.error_template
        )

    def handle_error(self, error):

        # Follow redirects
        if error.redirect_url is not None:
            return redirect(error.redirect_url)

        # Render error page
        # todo: use message / data from exception in error page
        error_data = error.to_data()
        return self.render(
            error_data,
            None,
            template_name=self.error_template
        ), error.code

    def load_file(self, template_file):
        """Load template file from template directory.

        :param template_file: Name of template file.
        :return: Template file

        """
        with open(os.path.join(self.template_dir, template_file), 'r') as f:
            loaded = f.read()
        return loaded

    def render_element(self, element, data):
        """Renders an embedded template.

        :param element: The template embed (HtmlElement).
             Ex: <div mod-meta='{"tpl": "name.html", "replace": true}'></div>
        :param data: Dictionary to be passed to the template as context
        :return: 2-tuple: (<result>, <flag: replace div>)
        """

        element_attributes = element.attrib
        attributes_string = element_attributes['mod-meta']
        element_meta = json.loads(attributes_string) # todo more robust jsonqa

        uri = element_meta.get('uri')
        is_replace = element_meta.get('replace', False)
        kwargs = element_meta.get('kwargs', {})
        view_kwargs = element_meta.get('view_kwargs', {})

        render_data = copy.deepcopy(data)
        render_data.update(kwargs)

        if uri:
            # Catch errors and return appropriate debug divs
            # todo: add debug parameter
            try:
                uri_data = call_url(uri, view_kwargs=view_kwargs)
                render_data.update(uri_data)
            except NotFound:
                return '<div>URI {} not found</div>'.format(uri), is_replace
            except Exception as error:
                return '<div>Error retrieving URI {}: {}</div>'.format(
                    uri,
                    repr(error)
                ), is_replace

        try:
            template_rendered = self._render(
                render_data,
                element_meta['tpl'],
            )
        except Exception as error:
            return '<div>Error rendering template {}: {}'.format(
                element_meta['tpl'],
                repr(error)
            ), is_replace

        return template_rendered, is_replace

    def _render(self, data, template_name=None):

        template_name = template_name or self.template_name
        # Catch errors and return appropriate debug divs
        # todo: add debug parameter
        try:
            template_file = self.load_file(template_name)
        except IOError:
            return '<div>Template {} not found.</div>'.format(template_name)

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

    def render(self, data, redirect_url, *args, **kwargs):

        # Follow redirects
        if redirect_url is not None:
            return redirect(redirect_url)

        template_name = kwargs.get('template_name')

        # Load extra data
        extra_data = self.data if isinstance(self.data, dict) else self.data()
        data.update({key: val for key, val in extra_data.iteritems() if key not in data})

        return self._render(data, template_name)
