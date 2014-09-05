# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts

from flask import Flask, url_for

from framework.routing import Rule, json_renderer, process_rules


class RuleTestCase(unittest.TestCase):

    def setUp(self):
        # create a new app for every test
        self.app = Flask(__name__)

    def _make_rule(self, **kwargs):
        def vf():
            return {}

        return Rule(
            kwargs.get('routes', ['/', ]),
            kwargs.get('methods', ['GET', ]),
            kwargs.get('view_func_or_data', vf),
            kwargs.get('renderer', json_renderer),
            kwargs.get('view_kwargs'),
        )

    def test_rule_single_route(self):
        r = self._make_rule(routes='/')
        assert_equal(r.routes, ['/', ])

    def test_rule_single_method(self):
        r = self._make_rule(methods='GET')
        assert_equal(r.methods, ['GET', ])

    def test_rule_lambda_view(self):
        r = self._make_rule(view_func_or_data=lambda: '')
        assert_true(callable(r.view_func_or_data))

    def test_url_for_simple(self):
        r = Rule(["/project/"], "get", view_func_or_data=dummy_view, renderer=json_renderer)
        process_rules(self.app, [r])
        with self.app.test_request_context():
            assert_equal(url_for("JSONRenderer__dummy_view"), "/project/")

    def test_url_for_with_argument(self):
        r = Rule(['/project/<pid>/'], "get", view_func_or_data=dummy_view2, renderer=json_renderer)
        process_rules(self.app, [r])
        with self.app.test_request_context():
            assert_equal(url_for("JSONRenderer__dummy_view2", pid=123), "/project/123/")

    def test_url_for_with_prefix(self):
        api_rule = Rule(["/project/"], "get", view_func_or_data=dummy_view3,
                renderer=json_renderer)
        process_rules(self.app, [api_rule], prefix="/api/v1")
        with self.app.test_request_context():
            assert_equal(url_for("JSONRenderer__dummy_view3"), "/api/v1/project/")


def dummy_view():
    return {'status': 'success'}

def dummy_view2(pid):
    return {"id": pid}

def dummy_view3():
    return {"status": "success"}
