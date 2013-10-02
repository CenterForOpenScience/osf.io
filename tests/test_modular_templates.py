import json
import unittest

import flask
import lxml
import werkzeug.wrappers

from framework.exceptions import HTTPError, http
from new_style import (
    Renderer, JSONRenderer, WebRenderer,
    render_mako_string,
    call_url,
)
from tests import OsfTestCase


class RendererTestCase(OsfTestCase):
    def setUp(self):
        super(RendererTestCase, self).setUp()
        self.r = Renderer()

    def test_redirect(self):
        """When passed a Flask/Werkzeug Response object, it should be returned.
        """
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.BaseResponse,
        )

    def test_http_error_raised(self):
        """Subclasses of Renderer must implement ``.handle_error()``."""
        with self.assertRaises(NotImplementedError):
            self.r(HTTPError(http.NOT_FOUND))

    def test_tuple(self):
        """Subclasses of Renderer must implement ``.render()``."""
        with self.assertRaises(NotImplementedError):
            self.r(('response text', ))


class JSONRendererTestCase(OsfTestCase):

    def setUp(self):
        super(JSONRendererTestCase, self).setUp()
        self.r = JSONRenderer()

    def test_redirect(self):
        """When passed a Flask/Werkzeug Response object, it should be returned.
        """
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.BaseResponse,
        )

    def test_http_error_raised(self):
        """When an HTTPError is raised in the view function, it is passed as
        input to the renderer.

        ``JSONRenderer`` should return a 2-tuple, where the first element is a
        dict representative of the error passed, and the second element is the
        associated HTTP status code. This mirrors the tuple format anticipated
        by Flask.
        """
        resp = self.r(HTTPError(http.NOT_FOUND))

        msg = HTTPError.error_msgs[http.NOT_FOUND]

        self.assertEqual(
            (
                {
                    'code': http.NOT_FOUND,
                    'referrer': None,
                    'message_short': msg['message_short'],
                    'message_long': msg['message_long'],
                },
                http.NOT_FOUND,
            ),
            (json.loads(resp[0]), http.NOT_FOUND, ),
        )

    def test_tuple(self):
        pass


class WebRendererTestCase(OsfTestCase):

    def setUp(self):
        super(WebRendererTestCase, self).setUp()
        self.r = WebRenderer(
            '../../tests/templates/main.html',
            render_mako_string
        )

    def test_redirect(self):
        """When passed a Flask-style tuple where the HTTP status code indicates
        a redirection should take place, a Flask/Werkzeug response object should
        be returned, with the appropriate ``status_code`` and ``location`` set.

        Note that this behavior is inconsistent with that of raising an
        ``HTTPError`` in a view function, which serves the same purpose.
        """
        with self.app.test_request_context():
            self.app.preprocess_request()

            resp = self.r(
                ({},  # data
                302,  # status code
                None,  # headers
                'http://google.com/',  # redirect_uri
                )
            )

            self.assertIsInstance(
                resp,
                werkzeug.wrappers.BaseResponse,
            )
            self.assertEqual(302, resp.status_code)
            self.assertEqual('http://google.com/', resp.location)

    def test_input_dict(self):
        """When only a dict is passed it, a Flask-style tuple is returned, of
        which the 0th element must be the rendered template, including the dict
        as part of the context.
        """
        with self.app.test_request_context():
            self.app.preprocess_request()

            input_dict = {'foo': 'bar'}

            resp = self.r(input_dict)

            self.assertIsInstance(
                resp, tuple
            )

            self.assertIn(
                'foo:bar',
                resp[0]
            )

    def test_http_error_raised(self):
        """When an HTTPError is raised in the view function, it is passed as
        input to the renderer.

        ``WebRenderer`` should return a 2-tuple, where the first element is the
        rendered error template. Each HTTPError exposes a ``to_data()`` method,
        which yields the appropriate error message text.
        """

        err = HTTPError(http.NOT_FOUND)

        resp = self.r(err)

        self.assertIn(
            err.to_data()['message_short'],
            resp[0],
        )
        self.assertEqual(
            http.NOT_FOUND,
            resp[1],
        )

    def test_http_error_raise_with_redirect(self):
        """Some status codes passed to HTTPError may contain a ``resource_uri``
        which specifies a location to which the user may be redirected. If a
        ``resource_uri`` is present, the ``WebRenderer`` should redirect the
        user to that URL.

        Note that some HTTP status codes - for example, 201 (Created) - are not
        well-supported by browser. As a result, while the 201 should be passed
        back to an API client, it is translated to a 301 when passed to
        ``WebRenderer``. This results in a website user being taken directly to
        a new object upon creation, instead of to an intermediate page.

        This functionality is technically a violation of the HTTP spec, and
        should be retired once we move to an API-centric web frontend.
        """
        resp = self.r(
            HTTPError(http.CREATED, resource_uri='http://google.com/')
        )

        self.assertIsInstance(
            resp, werkzeug.wrappers.BaseResponse
        )

        self.assertEqual(302, resp.status_code)
        self.assertEqual('http://google.com/', resp.location)


class WebRendererTemplateTestCase(OsfTestCase):

    def test_nested_templates(self):
        """When a template passed to ``WebRenderer`` contains references to
        nested templates, those nested templates should be rendered recursively
        prior to return."""

        with self.app.test_request_context():
            self.app.preprocess_request()

            # Create a ``WebRenderer`` for a nested template file.
            r = WebRenderer(
                'nested_parent.html',
                render_mako_string,
                template_dir='tests/templates',
            )

            # render the template (with an empty context)
            resp = r({})

            # The result should be a tuple
            self.assertIsInstance(resp, tuple)
            # The contents of the inner template should be present in the page.
            self.assertIn('child template content', resp[0])

    def test_render_included_template(self):
        """``WebRenderer.render_element()`` is the internal method called when
        a template string is rendered. This test case examines the same
        functionality as ``test_nested_templates()`` (above), but does so
        without relying on the parent template being found and processed.
        """
        with self.app.test_request_context():
            self.app.preprocess_request()

            r = WebRenderer(
                'nested_child.html',
                render_mako_string,
                template_dir='tests/templates',
            )

            html = lxml.html.fragment_fromstring(
                ''.join((
                    "<div mod-meta='",
                    '{"tpl":"nested_child.html","replace": true}',
                    "'></div>",
                )),
                create_parent='remove-me',
            )

            result = r.render_element(
                html.findall('.//*[@mod-meta]')[0],
                data={},
            )

            self.assertEqual(
                ('<p>child template content</p>', True),
                result,
            )

    @unittest.skip('Fails with IOError - should replace the template content')
    def test_broken_template_uri(self):
        """When a template contains an embedded template that can't be found,
        a message indicating that should be included in the rendered page.

        NOTE: This functionality is currently failing. Instead of including the
        appropriate message in the output, an IOError is raised.
        """
        with self.app.test_request_context():
            self.app.preprocess_request()

            r = WebRenderer(
                'nested_parent_broken.html',
                render_mako_string,
                template_dir='tests/templates',
            )

            resp = r({})

            self.assertIn(
                'URI {} not found.'.format(
                    'test/templates/not_a_valid_file.html'),
                resp[0],
            )

    @unittest.skip('Fails with IOError - should replace the template content')
    def test_render_included_template_not_found(self):
        """``WebRenderer.render_element()`` is the internal method called when
        a template string is rendered. This test case examines the same
        functionality as ``test_broken_template_uri()`` (above), but does so
        without relying on the parent template being found and processed.
        """
        with self.app.test_request_context():
            self.app.preprocess_request()

            r = WebRenderer(
                'nested_child.html',
                render_mako_string,
                template_dir='tests/templates',
            )

            html = lxml.html.fragment_fromstring(
                ''.join((
                    "<div mod-meta='",
                    '{"tpl":"not_a_real_file.html","replace": true}',
                    "'></div>",
                )),
                create_parent='remove-me',
            )

            result = r.render_element(
                html.findall('.//*[@mod-meta]')[0],
                data={},
            )

            self.assertEqual(
                ('<p>child template content</p>', True),
                result,
            )


class CallUriTestCase(OsfTestCase):

    def test_call_homepage(self):
        with self.app.test_request_context():
            self.app.preprocess_request()

            r = call_url('/', wrap=True)