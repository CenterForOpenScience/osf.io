# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa

import functools
from contextlib import nested
from types import MethodType

from rest_framework import generics
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate
)

from tests.base import ApiTestCase
from tests import factories

from api.base.settings.defaults import API_BASE
from api.nodes import views as node_views

def spy_on(method):

    calls = []
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return method(*args, **kwargs)

    return calls, wrapper

        
class TestJSONAPISerializer(ApiTestCase):

    def setUp(self):
        super(TestJSONAPISerializer, self).setUp()
        
        self.user = factories.AuthUserFactory()
        self.node = factories.ProjectFactory(creator=self.user)
        self.url = '/{0}nodes/{1}/'.format(API_BASE, self.node._id)
        for i in range(5):
            factories.ProjectFactory(parent=self.node, creator=self.user)
        for i in range(5):
            factories.ProjectFactory(parent=self.node)

    def test_included_fields_are_added_to_response(self):
        includes = ['children', 'parent']
        res = self.app.get(
            self.url,
            auth=self.user.auth,
            params={
                'include': includes
            }
        )
        for include in includes:
            assert_in(include, res.json['data']['includes'])


    def test_sideload_attempts_with_errors_are_None(self):
        res = self.app.get(
            self.url,
            auth=self.user.auth,
            params={
                'include': ['parent']
            }
        )
        assert_is_none(res.json['data']['includes']['parent'])
	        
