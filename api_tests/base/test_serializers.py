# -*- coding: utf-8 -*-
import httplib as http

from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase, DbTestCase
from tests import factories
from tests.utils import make_drf_request

from api.base.settings.defaults import API_BASE
from api.base.serializers import JSONAPISerializer
from api.nodes.serializers import NodeSerializer, JSONAPIHyperlinkedIdentityField

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
            if (field.meta or {}).get('count'):
                link = relation['links'].values()[0]
                assert_in('count', link['meta'])

    def test_related_counts_excluded_query_param_false(self):

        res = self.app.get(self.url, params={'related_counts': False})
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            link = relation['links'].values()[0]
            assert_not_in('count', link['meta'])

    def test_invalid_related_counts_value_raises_bad_request(self):

        res = self.app.get(self.url, params={'related_counts': 'fish'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_invalid_embed_value_raise_bad_request(self):
        res = self.app.get(self.url, params={'embed': 'foo'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(res.json['errors'][0]['detail'], "Field 'foo' is not embeddable.")


class TestJSONAPIHyperlinkedIdentityField(DbTestCase):

    # We need a Serializer to test the JSONHyperlinkedIdentity field (needs context)
    class BasicNodeSerializer(JSONAPISerializer):
        parent = JSONAPIHyperlinkedIdentityField(
            view_name='nodes:node-detail',
            lookup_field='pk',
            lookup_url_kwarg='node_id',
            link_type='related'
        )

        parent_with_meta = JSONAPIHyperlinkedIdentityField(
            view_name='nodes:node-detail',
            lookup_field='pk',
            lookup_url_kwarg='node_id',
            link_type='related',
            meta={'count': 'get_count', 'extra': 'get_extra'}
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
