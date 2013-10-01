import json

import flask
import werkzeug.wrappers

from framework.exceptions import HTTPError, http
from new_style import Renderer, JSONRenderer
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
            ( json.loads(resp[0]), http.NOT_FOUND, ),
        )