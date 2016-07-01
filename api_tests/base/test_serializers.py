# -*- coding: utf-8 -*-
import httplib as http
import contextlib
import mock

from nose.tools import *  # flake8: noqa
import re

from tests.base import ApiTestCase, DbTestCase
from tests import factories
from tests.utils import make_drf_request

from api.base.settings.defaults import API_BASE
from api.base.serializers import JSONAPISerializer
from api.base import serializers as base_serializers
from api.nodes.serializers import NodeSerializer, RelationshipField
from api.registrations.serializers import RegistrationSerializer


class FakeModel(object):

    def null_field(self):
        return None

    def valued_field(self):
        return 'Some'

    null = None
    foo = 'bar'

    pk = '1234'

class FakeSerializer(base_serializers.JSONAPISerializer):

    class Meta:
        type_ = 'foos'

    links = base_serializers.LinksField({
        'null_field': 'null_field',
        'valued_field': 'valued_field',
    })
    null_link_field = base_serializers.RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<null>'},
    )
    valued_link_field = base_serializers.RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<foo>'},
    )
    def null_field(*args, **kwargs):
        return None

    def valued_field(*args, **kwargs):
        return 'http://foo.com'


class TestNodeSerializerAndRegistrationSerializerDifferences(ApiTestCase):
    """
    All fields on the Node Serializer other than the few we can serialize for withdrawals must be redeclared on the
    Registration Serializer and wrapped in HideIfWithdrawal

    HideIfRegistration fields should not be serialized on registrations.
    """

    def setUp(self):
        super(TestNodeSerializerAndRegistrationSerializerDifferences, self).setUp()

        self.node = factories.ProjectFactory(is_public=True)
        self.registration = factories.RegistrationFactory(project = self.node, is_public=True)

        self.url = '/{}nodes/{}/'.format(API_BASE, self.node._id)
        self.reg_url = '/{}registrations/{}/'.format(API_BASE, self.registration._id)

    def test_registration_serializer(self):

        # fields that are visible for withdrawals
        visible_on_withdrawals = ['contributors', 'date_created', 'description', 'id', 'links', 'registration', 'title', 'type']
        # fields that do not appear on registrations
        non_registration_fields = ['registrations', 'draft_registrations']

        for field in NodeSerializer._declared_fields:
            assert_in(field, RegistrationSerializer._declared_fields)
            reg_field = RegistrationSerializer._declared_fields[field]

            if field not in visible_on_withdrawals and field not in non_registration_fields:
                assert_true(isinstance(reg_field, base_serializers.HideIfWithdrawal))

    def test_hide_if_registration_fields(self):

        node_res = self.app.get(self.url)
        node_relationships = node_res.json['data']['relationships']

        registration_res = self.app.get(self.reg_url)
        registration_relationships = registration_res.json['data']['relationships']

        hide_if_registration_fields = [field for field in NodeSerializer._declared_fields if isinstance(NodeSerializer._declared_fields[field], base_serializers.HideIfRegistration)]

        for field in hide_if_registration_fields:
            assert_in(field, node_relationships)
            assert_not_in(field, registration_relationships)


class TestNullLinks(ApiTestCase):

    def test_null_links_are_omitted(self):
        req = make_drf_request()
        rep = FakeSerializer(FakeModel, context={'request': req}).data['data']

        assert_not_in('null_field', rep['links'])
        assert_in('valued_field', rep['links'])
        assert_not_in('null_link_field', rep['relationships'])
        assert_in('valued_link_field', rep['relationships'])



class TestApiBaseSerializers(ApiTestCase):

    def setUp(self):
        super(TestApiBaseSerializers, self).setUp()

        self.node = factories.ProjectFactory(is_public=True)

        for i in range(5):
            factories.ProjectFactory(is_public=True, parent=self.node)

        self.url = '/{}nodes/{}/'.format(API_BASE, self.node._id)

    def test_serializers_have_get_absolute_url_method(self):
        serializers = JSONAPISerializer.__subclasses__()
        base_get_absolute_url = JSONAPISerializer.get_absolute_url

        for serializer in serializers:
            if not re.match('^(api_test|test).*', serializer.__module__):
                assert hasattr(serializer, 'get_absolute_url'), 'No get_absolute_url method'
                assert_not_equal(serializer.get_absolute_url, base_get_absolute_url)

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
            if getattr(field, 'field', None):
                field = field.field
            if (field.related_meta or {}).get('count'):
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

    def test_invalid_related_counts_value_raises_bad_request(self):

        res = self.app.get(self.url, params={'related_counts': 'fish'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_invalid_embed_value_raise_bad_request(self):
        res = self.app.get(self.url, params={'embed': 'foo'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(res.json['errors'][0]['detail'], "The following fields are not embeddable: foo")

    def test_embed_does_not_remove_relationship(self):
        res = self.app.get(self.url, params={'embed': 'root'})
        assert_equal(res.status_code, 200)
        assert_in(self.url, res.json['data']['relationships']['root']['links']['related']['href'])

    def test_counts_included_in_children_field_with_children_related_counts_query_param(self):

        res = self.app.get(self.url, params={'related_counts': 'children'})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if getattr(field, 'field', None):
                field = field.field
            link = relation['links'].values()[0]
            if (field.related_meta or {}).get('count') and key == 'children':
                assert_in('count', link['meta'])
            else:
                assert_not_in('count', link['meta'])

    def test_counts_included_in_children_and_contributors_fields_with_field_csv_related_counts_query_param(self):

        res = self.app.get(self.url, params={'related_counts': 'children,contributors'})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if getattr(field, 'field', None):
                field = field.field
            link = relation['links'].values()[0]
            if (field.related_meta or {}).get('count') and key == 'children' or key == 'contributors':
                assert_in('count', link['meta'])
            else:
                assert_not_in('count', link['meta'])

    def test_error_when_requesting_related_counts_for_attribute_field(self):

        res = self.app.get(self.url, params={'related_counts': 'title'}, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(res.json['errors'][0]['detail'], "Acceptable values for the related_counts query param are 'true', 'false', or any of the relationship fields; got 'title'")



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

        # If related_view_kwargs is a callable, this field _must_ match the property name on
        # the target record
        registered_from = RelationshipField(
            related_view=lambda n: 'registrations:registration-detail' if n and n.is_registration else 'nodes:node-detail',
            related_view_kwargs=lambda n: {
                'node_id': '<registered_from_id>'
            }
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

    def test_field_with_callable_related_attrs(self):
        req = make_drf_request()
        project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=project)
        data = self.BasicNodeSerializer(node, context={'request': req}).data['data']
        assert_not_in('registered_from', data['relationships'])

        registration = factories.RegistrationFactory(project=node)
        data = self.BasicNodeSerializer(registration, context={'request': req}).data['data']
        field = data['relationships']['registered_from']['links']
        assert_in('/v2/nodes/{}/'.format(node._id), field['related']['href'])

        registration_registration = factories.RegistrationFactory(project=registration)
        data = self.BasicNodeSerializer(registration_registration, context={'request': req}).data['data']
        field = data['relationships']['registered_from']['links']
        assert_in('/v2/registrations/{}/'.format(registration._id), field['related']['href'])
