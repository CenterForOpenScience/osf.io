# -*- coding: utf-8 -*-
import unittest

from nose.tools import *  # noqa (PEP8 asserts)
from flask import Flask
from webtest_plus import TestApp

from framework.exceptions import HTTPError
from framework.routing import json_renderer, process_rules, Rule

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

        self.wt = TestApp(self.app)

    def test_error_handling(self):
        rule = Rule(['/error/'], 'get', error_view, renderer=json_renderer)
        process_rules(self.app, [rule])
        res = self.wt.get('/error/', expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_true(isinstance(res.json, dict))

    def test_error_handling_with_message(self):
        rule = Rule(['/error/'], 'get', error_with_msg, renderer=json_renderer)
        process_rules(self.app, [rule])
        res = self.wt.get('/error/', expect_errors=True)
        assert_equal(res.status_code, 400)
        data = res.json
        assert_equal(data['message_short'], 'Invalid')
        assert_equal(data['message_long'], 'Invalid request')
