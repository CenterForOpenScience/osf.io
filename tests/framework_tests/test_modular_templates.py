# -*- coding: utf-8 -*-
'''Unit tests for the modular template system.

These require a test db because they use Session objects.
'''
import json
import unittest
import os

import flask
from lxml.html import fragment_fromstring
import werkzeug.wrappers

from rest_framework import status as http_status
from framework.exceptions import HTTPError
from framework.routing import (
    Renderer, JSONRenderer, WebRenderer,
    render_mako_string,
)

from tests.base import AppTestCase, OsfTestCase

# Need to use OsfWebRenderer to get global variables
from website.routes import OsfWebRenderer

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(HERE, 'templates')


class RendererTestCase(AppTestCase):
    def setUp(self):
        super(RendererTestCase, self).setUp()
        self.r = Renderer()

    def test_redirect(self):
        """When passed a Flask/Werkzeug Response object, it should be returned.
        """
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.Response,
        )

    def test_http_error_raised(self):
        """Subclasses of Renderer must implement ``.handle_error()``."""
        with self.assertRaises(NotImplementedError):
            self.r(HTTPError(http_status.HTTP_404_NOT_FOUND))

    def test_tuple(self):
        """Subclasses of Renderer must implement ``.render()``."""
        with self.assertRaises(NotImplementedError):
            self.r(('response text', ))


class JSONRendererTestCase(RendererTestCase):

    def setUp(self):
        super(JSONRendererTestCase, self).setUp()
        self.r = JSONRenderer()

    def test_redirect(self):
        """When passed a Flask/Werkzeug Response object, it should be returned.
        """
        resp = flask.make_response('')

        self.assertIsInstance(
            self.r(resp),
            werkzeug.wrappers.Response,
        )

    def test_http_error_raised(self):
        """When an HTTPError is raised in the view function, it is passed as
        input to the renderer.

        ``JSONRenderer`` should return a 2-tuple, where the first element is a
        dict representative of the error passed, and the second element is the
        associated HTTP status code. This mirrors the tuple format anticipated
        by Flask.
        """
        resp = self.r(HTTPError(http_status.HTTP_404_NOT_FOUND))

        msg = HTTPError.error_msgs[http_status.HTTP_404_NOT_FOUND]

        self.assertEqual(
            (
                {
                    'code': http_status.HTTP_404_NOT_FOUND,
                    'referrer': None,
                    'message_short': msg['message_short'],
                    'message_long': msg['message_long'],
                },
                http_status.HTTP_404_NOT_FOUND,
            ),
            (json.loads(resp[0]), http_status.HTTP_404_NOT_FOUND, ),
        )

    def test_tuple(self):
        pass


class WebRendererTestCase(OsfTestCase):

    def setUp(self):
        super(WebRendererTestCase, self).setUp()

        # Use OsfRenderer so that global vars are included
        self.r = OsfWebRenderer(
            os.path.join(TEMPLATES_PATH, 'main.html'),
            render_mako_string
        )

    def test_redirect(self):
        """When passed a Flask-style tuple where the HTTP status code indicates
        a redirection should take place, a Flask/Werkzeug response object should
        be returned, with the appropriate ``status_code`` and ``location`` set.

        Note that this behavior is inconsistent with that of raising an
        ``HTTPError`` in a view function, which serves the same purpose.
        """
        self.app.app.preprocess_request()

        resp = self.r(
            ({},  # data
            302,  # status code
            None,  # headers
            'http://google.com/',  # redirect_uri
            )
        )

        self.assertIsInstance(
            resp,
            werkzeug.wrappers.Response,
        )
        self.assertEqual(302, resp.status_code)
        self.assertEqual('http://google.com/', resp.location)

    def test_input_dict(self):
        """When only a dict is passed it, a Flask-style tuple is returned, of
        which the 0th element must be the rendered template, including the dict
        as part of the context.
        """
        self.app.app.preprocess_request()

        input_dict = {'foo': 'bar'}

        resp = self.r(input_dict)

        self.assertIsInstance(
            resp, werkzeug.wrappers.Response
        )

        self.assertIn(
            'foo:bar',
            resp.data
        )

    def test_http_error_raised(self):
        """When an HTTPError is raised in the view function, it is passed as
        input to the renderer.

        ``WebRenderer`` should return a 2-tuple, where the first element is the
        rendered error template. Each HTTPError exposes a ``to_data()`` method,
        which yields the appropriate error message text.
        """

        self.app.app.preprocess_request()

        err = HTTPError(http_status.HTTP_404_NOT_FOUND)

        resp = self.r(err)

        self.assertIn(
            err.to_data()['message_short'],
            resp[0],
        )
        self.assertEqual(
            http_status.HTTP_404_NOT_FOUND,
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
            HTTPError(http_status.HTTP_201_CREATED, redirect_url='http://google.com/')
        )

        self.assertIsInstance(
            resp, werkzeug.wrappers.Response
        )

        self.assertEqual(302, resp.status_code)
        self.assertEqual('http://google.com/', resp.location)

class JSONRendererEncoderTestCase(unittest.TestCase):

    def test_encode_custom_class(self):

        class TestClass(object):
            def to_json(self):
                return '<JSON representation>'

        test_object = TestClass()

        self.assertEqual(
            '"<JSON representation>"',
            json.dumps(test_object, cls=JSONRenderer.Encoder),
        )

    def test_string(self):
        self.assertEqual(
            '"my string"',
            json.dumps('my string', cls=JSONRenderer.Encoder)
        )
