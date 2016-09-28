# -*- coding: utf-8 -*-
import unittest

from nose.tools import *  # noqa (PEP8 asserts)
from flask import Flask
from webtest_plus import TestApp

from framework.exceptions import HTTPError
from framework.routing import json_renderer, process_rules, Rule

from tests import factories
from tests.base import OsfTestCase

from website import routes
from website import settings

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


class TestGetGlobals(OsfTestCase):

    def setUp(self):
        super(TestGetGlobals, self).setUp()

        self.inst_one = factories.InstitutionFactory()
        self.inst_two = factories.InstitutionFactory()

        self.user = factories.AuthUserFactory()
        self.user.affiliated_institutions.append(self.inst_one)
        self.user.affiliated_institutions.append(self.inst_two)
        self.user.save()

        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD):
            node = factories.NodeFactory(creator=self.user, is_public=True)
            node.affiliated_institutions.append(self.inst_one)
            node.save()

        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD - 1):
            node = factories.NodeFactory(creator=self.user, is_public=True)
            node.affiliated_institutions.append(self.inst_two)
            node.save()

    def test_get_globals_dashboard_institutions(self):
        globals = routes.get_globals()
        dashboard_institutions = globals['dashboard_institutions']
        assert_equal(len(dashboard_institutions), 1)
        assert_equal(dashboard_institutions[0]['id'], self.inst_one._id)
        assert_not_equal(dashboard_institutions[0]['id'], self.inst_two._id)
