# -*- coding: utf-8 -*-
from api.base.wsgi import application

from nose.tools import *  # flake8: noqa
import httplib as http
import contextlib
import mock

from rest_framework import serializers as ser

from tests.base import ApiTestCase
from tests import factories

from api.base.settings.defaults import API_BASE
from api.base import serializers as base_serializers
from api.nodes.serializers import NodeSerializer

FakeModel = mock.Mock

class FakeSerializer(base_serializers.JSONAPISerializer):

    class Meta:
        type_ = 'foos'

    links = base_serializers.LinksField({
        'null_field': 'null_field',
        'valued_field': 'valued_field',
        'null_wb_field': base_serializers.WaterbutlerLink(kind='file', null=True),
        'valued_wb_field':  base_serializers.WaterbutlerLink(kind='file')
    })
    
    null_link_field = base_serializers.JSONAPIHyperlinkedIdentityField(
        'null:bar',
        lookup_field='foo',
        lookup_url_kwarg='bar',
        link_type='related'
    )
    valued_link_field = base_serializers.JSONAPIHyperlinkedIdentityField(
        'foo:bar',
        lookup_field='foo',
        lookup_url_kwarg='bar',
        link_type='related'
    )

    def null_field(*args, **kwargs):
        return None

    def valued_field(*args, **kwargs):
        return 'http://foo.com'

def mock_hyperlink(instance, view_name, *args, **kwargs):
    if view_name == 'null:bar':
        return None
    else:
        return 'http://foo.com'

def mock_wb_link(*args, **kwargs):
    return 'http://api.foo.com' if not kwargs.get('null', False) else None

class TestNullLinks(ApiTestCase):

    def test_null_links_are_omitted(self):
        ser = FakeSerializer()
        with contextlib.nested(
                mock.patch(
                    'rest_framework.relations.HyperlinkedRelatedField.context',
                    mock.Mock(return_value={
                        'request': mock.Mock()
                    })
                ),
                mock.patch(
                    'rest_framework.relations.HyperlinkedRelatedField.get_url',
                    mock.Mock(side_effect=mock_hyperlink)
                ),                
                mock.patch(
                    'website.util.waterbutler_api_url_for',
                    mock.Mock(side_effect=mock_wb_link)
                )
        ):
            model = FakeModel()
            rep = ser.to_representation(model)['data']
            assert_not_in('null_field', rep['links'])
            assert_in('valued_field', rep['links'])
            assert_not_in('null_wb_field', rep['links'])
            assert_in('valued_wb_field', rep['links'])            
            assert_not_in('null_link_field', rep['relationships'])
            assert_in('valued_link_field', rep['relationships'])


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
            if relation == {}:
                continue
            link = relation['links'].values()[0]
            assert_not_in('count', link['meta'])

    def test_counts_included_in_link_fields_with_related_counts_query_param(self):

        res = self.app.get(self.url, params={'related_counts': True})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if (field.meta or {}).get('count'):            
                link = relation['links'].values()[0]
                assert_in('count', link['meta'])

    def test_related_counts_excluded_query_param_false(self):

        res = self.app.get(self.url, params={'related_counts': False})
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            if relation == {}:
                continue
            link = relation['links'].values()[0]
            assert_not_in('count', link['meta'])

    def test_invalid_param_raises_bad_request(self):

        res = self.app.get(self.url, params={'related_counts': 'fish'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_self_link_is_unwrapped_url(self):
        res = self.app.get(self.url)

        assert_true(isinstance(res.json['data']['links']['self'], basestring))

    def test_null_link_formatting(self):
        res = self.app.get(self.url)

        assert_not_in('parent', res.json['data']['relationships'])
