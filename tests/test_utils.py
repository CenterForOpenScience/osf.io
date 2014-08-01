# -*- coding: utf-8 -*-
import unittest
from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)

from framework.routing import Rule, json_renderer
from website.routes import process_rules, OsfWebRenderer
from website.app import init_app
from website.util import web_url_for, api_url_for, is_json_request

app = init_app(set_backends=False)


class TestUrlForHelpers(unittest.TestCase):

    def setUp(self):
        def dummy_view(pid):
            return {}
        self.app = Flask(__name__)

        api_rule = Rule([
            '/api/v1/<pid>/',
            '/api/v1/<pid>/component/<nid>/'
        ], 'get', dummy_view, json_renderer)
        web_rule = Rule([
            '/<pid>/',
            '/<pid>/component/<nid>/'
        ], 'get', dummy_view, OsfWebRenderer)

        process_rules(self.app, [api_rule, web_rule])

    def test_api_url_for(self):
        with self.app.test_request_context():
            assert api_url_for('dummy_view', pid='123') == '/api/v1/123/'

    def test_web_url_for(self):
        with self.app.test_request_context():
            assert web_url_for('dummy_view', pid='123') == '/123/'

    def test_api_url_for_with_multiple_urls(self):
        with self.app.test_request_context():
            url = api_url_for('dummy_view', pid='123', nid='abc')
            assert url == '/api/v1/123/component/abc/'

    def test_web_url_for_with_multiple_urls(self):
        with self.app.test_request_context():
            url = web_url_for('dummy_view', pid='123', nid='abc')
            assert url == '/123/component/abc/'


def test_is_json_request():
    with app.test_request_context(content_type='application/json'):
        assert_true(is_json_request())
    with app.test_request_context(content_type=None):
        assert_false(is_json_request())
    with app.test_request_context(content_type='application/json;charset=UTF-8'):
        assert_true(is_json_request())
