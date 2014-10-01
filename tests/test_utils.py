# -*- coding: utf-8 -*-
import os
import unittest
from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)

from framework.routing import Rule, json_renderer
from website.routes import process_rules, OsfWebRenderer
from website.util import web_url_for, api_url_for, is_json_request
from website.util.mimetype import get_mimetype

try:
    import magic
    LIBMAGIC_AVAILABLE = True
except ImportError:
    LIBMAGIC_AVAILABLE = False

HERE = os.path.dirname(os.path.abspath(__file__))

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

    def test_is_json_request(self):
        with self.app.test_request_context(content_type='application/json'):
            assert_true(is_json_request())
        with self.app.test_request_context(content_type=None):
            assert_false(is_json_request())
        with self.app.test_request_context(content_type='application/json;charset=UTF-8'):
            assert_true(is_json_request())


class TestGetMimeTypes(unittest.TestCase):
    def test_get_markdown_mimetype_from_filename(self):
        name = 'test.md'
        mimetype = get_mimetype(name)
        assert_equal('text/x-markdown', mimetype)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_no_contents_not_real_file_results_in_exception(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        with assert_raises(IOError):
            get_mimetype(name)

    @unittest.skipIf(LIBMAGIC_AVAILABLE, 'This test only runs if python-magic and libmagic are not installed')
    def test_unknown_extension_with_no_contents_not_real_file_results_in_exception(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        mime_type = get_mimetype(name)
        assert_equal(None, mime_type)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_real_file_results_in_python_mimetype(self):
        name = 'test_views.notarealfileextension'
        maybe_python_file = os.path.join(HERE, 'test_files', name)
        mimetype = get_mimetype(maybe_python_file)
        assert_equal('text/x-python', mimetype)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_python_contents_results_in_python_mimetype(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        python_file = os.path.join(HERE, 'test_utils.py')
        with open(python_file, 'r') as the_file:
            content = the_file.read()
        mimetype = get_mimetype(name, content)
        assert_equal('text/x-python', mimetype)
