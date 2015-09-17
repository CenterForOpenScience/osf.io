# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests import factories

from api.base.settings.defaults import API_BASE
from api.nodes.serializers import NodeSerializer

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
            assert_not_in('count', link.get('meta', {}))

    def test_counts_included_in_link_fields_with_related_counts_query_param(self):

        res = self.app.get(self.url, params={'related_counts': True})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            field = NodeSerializer._declared_fields[key]
            if (field.meta or {}).get('count'):            
                link = relation['links'].values()[0]
                assert_in('count', link.get('meta', {}))

    def test_related_counts_excluded_query_param_false(self):

        res = self.app.get(self.url, params={'related_counts': False})
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            link = relation['links'].values()[0]
            assert_not_in('count', link.get('meta', {}))

