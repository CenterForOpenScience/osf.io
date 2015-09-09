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

    def test_each_included_fields_corresponding_view_is_called(self):
        includs = ['children', 'contributors']
        node_detail_calls, node_detail_wrapped = spy_on(node_views.NodeDetail.get)
        node_views.NodeDetail.get = MethodType(node_detail_wrapped, None, node_views.NodeDetail)
        node_contrib_calls, node_contrib_wrapped = spy_on(node_views.NodeContributorsList.get)
        node_views.NodeContributorsList.get = MethodType(node_contrib_wrapped, None, node_views.NodeContributorsList)
        self.app.get(
            self.url,
            auth=self.user.auth,
            params={
                'include': ['children', 'contributors']
            }
        )
        assert_equal(len(node_detail_calls), 1)
        assert_equal(len(node_contrib_calls), 1)
        
