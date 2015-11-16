# -*- coding: utf-8 -*-
import httplib as http

from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase, DbTestCase
from tests import factories
from tests.utils import make_drf_request

from api.base.settings.defaults import API_BASE
from api.base.serializers import JSONAPISerializer
from api.nodes.serializers import NodeSerializer, RelationshipField


class TestApiBaseSerializers(ApiTestCase):

    def setUp(self):
        super(TestApiBaseSerializers, self).setUp()

        self.node = factories.ProjectFactory(is_public=True)

        for i in range(5):
            factories.ProjectFactory(is_public=True, parent=self.node)

        self.url = '/{}nodes/{}/'.format(API_BASE, self.node._id)

    def test_counts_not_included_in_link_fields_by_default(self):

        res = self.app.get(self.url)
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            link = relation['links'].values()[0]
            assert_not_in('count', link['meta'])

    def test_counts_included_in_link_fields_with_related_counts_query_param(self):

        res = self.app.get(self.url, params={'related_counts': True})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            field = NodeSerializer._declared_fields[key]
            if (field.related_meta or {}).get('count'):
                link = relation['links'].values()[0]
                assert_in('count', link['meta'])

    def test_related_counts_excluded_query_param_false(self):

        res = self.app.get(self.url, params={'related_counts': False})
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            link = relation['links'].values()[0]
            assert_not_in('count', link['meta'])

    def test_invalid_param_raises_bad_request(self):

        res = self.app.get(self.url, params={'related_counts': 'fish'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)


class TestRelationshipField(DbTestCase):

    # We need a Serializer to test the Relationship field (needs context)
    class BasicNodeSerializer(JSONAPISerializer):

        parent = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<pk>'}
        )

        parent_with_meta = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<pk>'},
            related_meta={'count': 'get_count', 'extra': 'get_extra'},
        )

        self_and_related_field = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<pk>'},
            self_view='nodes:node-contributors',
            self_view_kwargs={'node_id': '<pk>'},
        )

        two_url_kwargs = RelationshipField(
            # fake url, for testing purposes
            related_view='nodes:node-pointer-detail',
            related_view_kwargs={'node_id': '<pk>', 'node_link_id': '<pk>'},
        )

        not_attribute_on_target = RelationshipField(
            # fake url, for testing purposes
            related_view='nodes:node-children',
            related_view_kwargs={'node_id': '12345'}
        )

        class Meta:
            type_ = 'nodes'

        def get_count(self, obj):
            return 1

        def get_extra(self, obj):
            return 'foo'

    # TODO: Expand tests

    # Regression test for https://openscience.atlassian.net/browse/OSF-4832
    def test_serializing_meta(self):
        req = make_drf_request()
        project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=project)
        data = self.BasicNodeSerializer(node, context={'request': req}).data['data']

        meta = data['relationships']['parent_with_meta']['links']['related']['meta']
        assert_not_in('count', meta)
        assert_in('extra', meta)
        assert_equal(meta['extra'], 'foo')

    def test_self_and_related_fields(self):
        req = make_drf_request()
        project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=project)
        data = self.BasicNodeSerializer(node, context={'request': req}).data['data']

        relationship_field = data['relationships']['self_and_related_field']['links']
        assert_in('/v2/nodes/{}/contributors/'.format(node._id), relationship_field['self']['href'])
        assert_in('/v2/nodes/{}/'.format(node._id), relationship_field['related']['href'])

    def test_field_with_two_kwargs(self):
        req = make_drf_request()
        project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=project)
        data = self.BasicNodeSerializer(node, context={'request': req}).data['data']
        field = data['relationships']['two_url_kwargs']['links']
        assert_in('/v2/nodes/{}/node_links/{}/'.format(node._id, node._id), field['related']['href'])

    def test_field_with_non_attribute(self):
        req = make_drf_request()
        project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=project)
        data = self.BasicNodeSerializer(node, context={'request': req}).data['data']
        field = data['relationships']['not_attribute_on_target']['links']
        assert_in('/v2/nodes/{}/children/'.format('12345'), field['related']['href'])
