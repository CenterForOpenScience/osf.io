import logging
import unittest

from flask import Flask

from framework.exceptions import HTTPError
from framework.routing import json_renderer, process_rules, Rule

logger = logging.getLogger(__name__)


def error_view():
    raise HTTPError(400)


def error_with_msg():
    raise HTTPError(400, data={
        'message_short': 'Invalid',
        'message_long': 'Invalid request'
    })


class TestJSONRenderer(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.debug = True

        self.wt = self.app.test_client()

        # logger.error('self.app has been changed from a webtest_plus.TestApp to a flask.Flask.test_client.')

    def test_error_handling(self):
        rule = Rule(['/error/'], 'get', error_view, renderer=json_renderer)
        process_rules(self.app, [rule])
        res = self.wt.get('/error/')
        assert res.status_code == 400
        assert isinstance(res.json, dict)

    def test_error_handling_with_message(self):
        rule = Rule(['/error/'], 'get', error_with_msg, renderer=json_renderer)
        process_rules(self.app, [rule])
        res = self.wt.get('/error/')
        assert res.status_code == 400
        data = res.json
        assert data['message_short'] == 'Invalid'
        assert data['message_long'] == 'Invalid request'
