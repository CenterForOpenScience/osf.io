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
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.BaseResponse,
        )

    def test_http_error_raised(self):
        with self.assertRaises(NotImplementedError):
            self.r(HTTPError(http.NOT_FOUND))

    def test_tuple(self):
        with self.assertRaises(NotImplementedError):
            self.r(('response text', ))


class JSONRendererTestCase(OsfTestCase):

    def setUp(self):
        super(JSONRendererTestCase, self).setUp()
        self.r = JSONRenderer()

    def test_redirect(self):
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.BaseResponse,
        )

    def test_http_error_raised(self):
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
            'index.html',
            render_mako_string
        )

    def test_redirect(self):
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
        with self.app.test_request_context():
            self.app.preprocess_request()

            resp = self.r({})

            self.assertIsInstance(
                resp, tuple
            )

    def test_http_error_raised(self):
        resp = self.r(HTTPError(http.NOT_FOUND))

        self.assertIn(
            HTTPError.error_msgs[http.NOT_FOUND]['message_short'],
            resp[0],
        )
        self.assertEqual(
            http.NOT_FOUND,
            resp[1],
        )

    def test_http_error_raise_with_redirect(self):
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
        with self.app.test_request_context():
            self.app.preprocess_request()

            r = WebRenderer(
                'nested_parent.html',
                render_mako_string,
                template_dir='tests/templates',
            )

            resp = r({})

            self.assertIsInstance(resp, tuple)
            self.assertIn('child template content', resp[0])

    @unittest.skip('Fails with IOError - should replace the template content')
    def test_broken_template_uri(self):
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

    def test_render_included_template(self):
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
    def test_render_included_template_not_found(self):
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

            print r