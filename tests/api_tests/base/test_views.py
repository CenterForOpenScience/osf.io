# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa

from rest_framework import generics
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate
)

from tests.base import ApiTestCase
from tests import factories

from framework.auth import Auth

from api.base.settings.defaults import API_BASE
from api.base.views import JSONAPIBaseView
from api.base.serializers import JSONAPIHyperlinkedIdentityField

from api.nodes.views import NodeDetail, NodeChildrenList

class TestApiBaseViews(ApiTestCase):

    def test_root_returns_200(self):
        res = self.app.get('/{}'.format(API_BASE))
        assert_equal(res.status_code, 200)

class TestJSONAPIBaseView(ApiTestCase):

    def setUp(self):
        super(TestJSONAPIBaseView, self).setUp()

        self.user = factories.AuthUserFactory()
        self.node = factories.ProjectFactory(creator=self.user)
        self.url = '/{0}nodes/{1}/'.format(API_BASE, self.node._id)
        for i in range(5):
            factories.ProjectFactory(parent=self.node, creator=self.user)
        for i in range(5):
            factories.ProjectFactory(parent=self.node)

    @mock.patch('api.base.serializers.JSONAPISerializer.to_representation', autospec=True)    
    def test_request_added_to_serializer_context(self, mock_to_representation):
        self.app.get(self.url, auth=self.user.auth)

        serializer_instance = mock_to_representation.call_args[0][0]
        assert_in('request', serializer_instance.context)        

    @mock.patch('api.base.serializers.JSONAPISerializer.to_representation', autospec=True)            
    def test_include_added_to_serializer_context_if_in_query_string(self, mock_to_representation):
        self.app.get(
            self.url,
            auth=self.user.auth,
            params={
                'include': 'children'
            }
        )
        serializer_instance = mock_to_representation.call_args[0][0]
        assert_in('include', serializer_instance.context)

    def test_include_values_are_partial_functions_that_return_data(self):
        request = APIRequestFactory().get(
            self.url + '?include=children',
            format='json'
        )
        force_authenticate(request, user=self.user)
        with mock.patch('api.base.serializers.JSONAPISerializer.to_representation', autospec=True) as mock_to_representation:
            NodeDetail.as_view()(
                request,
                node_id=self.node._id,
            )
        serializer_instance = mock_to_representation.call_args[0][0]
        serialize_children = serializer_instance.context['include']['children']
        partial_response = serialize_children(request, self.node)

        request = APIRequestFactory().get(
            self.url,
            format='json'
        )
        force_authenticate(request, user=self.user)
        children_response = NodeChildrenList.as_view()(
            request,
            node_id=self.node._id
        )
        assert_equal(children_response.data['data'], partial_response)

    @mock.patch('api.base.serializers.JSONAPISerializer.to_representation', autospec=True)                    
    def test_include_not_added_to_serializer_context_if_no_inludes_as_view_kwarg(self, mock_to_representation):
        # Call the NodeDetail view directly
        # see: http://www.django-rest-framework.org/api-guide/testing/#forcing-authentication
        request = APIRequestFactory().get(
            self.url + '?include=children',
            format='json',
        )
        force_authenticate(request, user=self.user)
        NodeDetail.as_view()(
            request,
            node_id=self.node._id,
            no_includes=True
        )
        serializer_instance = mock_to_representation.call_args[0][0]
        assert_not_in('include', serializer_instance.context)
