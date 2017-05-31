from json import dumps
from django.core.handlers.wsgi import WSGIHandler
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test.signals import template_rendered
from django.core import signals
from django.test.client import store_rendered_templates
from django.utils.functional import curry
try:
    from django.db import close_old_connections
except ImportError:
    from django.db import close_connection
    close_old_connections = None

from webtest.utils import NoDefault
from webtest_plus import TestApp

class JSONAPIWrapper(object):
    """
    Creates wrapper with stated content_type.
    """
    def make_wrapper(self, url, method, content_type, params=NoDefault, **kw):
        """
        Helper method for generating wrapper method.
        """

        if params is not NoDefault:
            params = dumps(params, cls=self.JSONEncoder)
        kw.update(
            params=params,
            content_type=content_type,
            upload_files=None,
        )
        wrapper = self._gen_request(method, url, **kw)

        subst = dict(lmethod=method.lower(), method=method)
        wrapper.__name__ = str('%(lmethod)s_json_api' % subst)

        return wrapper


class JSONAPITestApp(TestApp, JSONAPIWrapper):
    """
    Extends TestApp to add json_api_methods(post, put, patch, and delete)
    which put content_type 'application/vnd.api+json' in header. Adheres to
    JSON API spec.
    """

    def __init__(self, *args, **kwargs):
        super(JSONAPITestApp, self).__init__(self.get_wsgi_handler(), *args, **kwargs)
        self.auth = None
        self.auth_type = 'basic'

    def get_wsgi_handler(self):
        return StaticFilesHandler(WSGIHandler())

    # From django-webtest (MIT Licensed, see NOTICE for license details)
    def do_request(self, req, status, expect_errors):

        # Django closes the database connection after every request;
        # this breaks the use of transactions in your tests.
        if close_old_connections is not None:  # Django 1.6+
            signals.request_started.disconnect(close_old_connections)
            signals.request_finished.disconnect(close_old_connections)
        else:  # Django < 1.6
            signals.request_finished.disconnect(close_connection)

        try:
            req.environ.setdefault('REMOTE_ADDR', '127.0.0.1')

            # is this a workaround for
            # https://code.djangoproject.com/ticket/11111 ?
            req.environ['REMOTE_ADDR'] = str(req.environ['REMOTE_ADDR'])
            req.environ['PATH_INFO'] = str(req.environ['PATH_INFO'])

            # Curry a data dictionary into an instance of the template renderer
            # callback function.
            data = {}
            on_template_render = curry(store_rendered_templates, data)
            template_rendered.connect(on_template_render)

            response = super(JSONAPITestApp, self).do_request(req, status,
                                                             expect_errors)

            # Add any rendered template detail to the response.
            # If there was only one template rendered (the most likely case),
            # flatten the list to a single element.
            def flattend(detail):
                if len(data[detail]) == 1:
                    return data[detail][0]
                return data[detail]

            response.context = None
            response.template = None
            response.templates = data.get('templates', None)

            if data.get('context'):
                response.context = flattend('context')

            if data.get('template'):
                response.template = flattend('template')
            elif data.get('templates'):
                response.template = flattend('templates')

            return response
        finally:
            if close_old_connections:  # Django 1.6+
                signals.request_started.connect(close_old_connections)
                signals.request_finished.connect(close_old_connections)
            else:  # Django < 1.6
                signals.request_finished.connect(close_connection)

    def json_api_method(method):

        def wrapper(self, url, params=NoDefault, bulk=False, **kw):
            content_type = 'application/vnd.api+json'
            if bulk:
                content_type = 'application/vnd.api+json; ext=bulk'
            return JSONAPIWrapper.make_wrapper(self, url, method, content_type, params, **kw)
        return wrapper

    post_json_api = json_api_method('POST')
    put_json_api = json_api_method('PUT')
    patch_json_api = json_api_method('PATCH')
    delete_json_api = json_api_method('DELETE')
