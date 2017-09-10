# -*- coding: utf-8 -*-
import httplib as http
import importlib
import pkgutil
import re

from datetime import datetime
import pytest
from pytz import utc
import urllib

# from tests.base import ApiTestCase, DbTestCase
from api.base.settings.defaults import API_BASE
from api.base.serializers import JSONAPISerializer, BaseAPISerializer
from api.base import serializers as base_serializers
from api.nodes.serializers import NodeSerializer, RelationshipField
from api.registrations.serializers import RegistrationSerializer
from osf_tests.factories import (
    Auth,
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
)
from tests.utils import make_drf_request_with_version


SER_MODULES = []
for loader, name, _ in pkgutil.iter_modules(['api']):
    if name != 'base' and name != 'test':
        try:
            SER_MODULES.append(importlib.import_module('api.{}.serializers'.format(name)))
        except ImportError:
            pass

SER_CLASSES = []
for mod in SER_MODULES:
    for name, val in mod.__dict__.iteritems():
        try:
            if issubclass(val, BaseAPISerializer):
                if 'JSONAPI' in name or 'BaseAPI' in name:
                    continue
                SER_CLASSES.append(val)
        except TypeError:
            pass

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


class TestSerializerMetaType:
    def test_expected_serializers_have_meta_types(self):
        for ser in SER_CLASSES:
            assert hasattr(ser, 'Meta'), 'Serializer {} has no Meta'.format(ser)
            assert hasattr(ser.Meta, 'type_'), 'Serializer {} has no Meta.type_'.format(ser)

@pytest.mark.django_db
class TestNodeSerializerAndRegistrationSerializerDifferences:
    """
    All fields on the Node Serializer other than the few we can serialize for withdrawals must be redeclared on the
    Registration Serializer and wrapped in HideIfWithdrawal

    HideIfRegistration fields should not be serialized on registrations.
    """

    def test_node_serializer_and_registration_serializer_differences(self, app):

        node = ProjectFactory(is_public=True)
        registration = RegistrationFactory(project=node, is_public=True)

        url = '/{}nodes/{}/'.format(API_BASE, node._id)
        url_reg = '/{}registrations/{}/'.format(API_BASE, registration._id)

        #test_registration_serializer
        # fields that are visible for withdrawals
        visible_on_withdrawals = ['contributors', 'date_created', 'date_modified', 'description', 'id', 'links', 'registration', 'title', 'type', 'current_user_can_comment', 'preprint']
        # fields that do not appear on registrations
        non_registration_fields = ['registrations', 'draft_registrations']

        for field in NodeSerializer._declared_fields:
            assert field in RegistrationSerializer._declared_fields
            reg_field = RegistrationSerializer._declared_fields[field]

            if field not in visible_on_withdrawals and field not in non_registration_fields:
                assert (isinstance(reg_field, base_serializers.HideIfWithdrawal)
                            or isinstance(reg_field, base_serializers.ShowIfVersion))

        #test_hide_if_registration_fields
        node_res = app.get(url)
        node_relationships = node_res.json['data']['relationships']

        registration_res = app.get(url_reg)
        registration_relationships = registration_res.json['data']['relationships']

        hide_if_registration_fields = [field for field in NodeSerializer._declared_fields if isinstance(NodeSerializer._declared_fields[field], base_serializers.HideIfRegistration)]

        for field in hide_if_registration_fields:
            assert field in node_relationships
            assert field not in registration_relationships

@pytest.mark.django_db
class TestNullLinks:

    def test_null_links_are_omitted(self):
        req = make_drf_request_with_version(version='2.0')
        rep = FakeSerializer(FakeModel, context={'request': req}).data['data']

        assert 'null_field' not in rep['links']
        assert 'valued_field' in rep['links']
        assert 'null_link_field' not in rep['relationships']
        assert 'valued_link_field' in rep['relationships']

@pytest.mark.django_db
class TestApiBaseSerializers:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        node = ProjectFactory(is_public=True)
        linked_node = NodeFactory(creator=user, is_public=True)
        node.add_pointer(linked_node, auth=Auth(user))
        for i in range(5):
            ProjectFactory(is_public=True, parent=node)
        return node

    @pytest.fixture()
    def url(self, node):
        return '/{}nodes/{}/'.format(API_BASE, node._id)

    def test_api_base_serializers(self, app, node, url):

        #test_serializers_have_get_absolute_url_method
        serializers = JSONAPISerializer.__subclasses__()
        base_get_absolute_url = JSONAPISerializer.get_absolute_url

        for serializer in serializers:
            if not re.match('^(api_test|test).*', serializer.__module__):
                assert hasattr(serializer, 'get_absolute_url'), 'No get_absolute_url method'
                assert serializer.get_absolute_url != base_get_absolute_url

        #test_counts_not_included_in_link_fields_by_default
        res = app.get(url)
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            if relation == {}:
                continue
            link = relation['links'].values()[0]
            assert 'count' not in link['meta']

        #test_counts_included_in_link_fields_with_related_counts_query_param
        res = app.get(url, params={'related_counts': True})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if getattr(field, 'field', None):
                field = field.field
            if (field.related_meta or {}).get('count'):
                link = relation['links'].values()[0]
                assert 'count' in link['meta'], field

        #test_related_counts_excluded_query_param_false
        res = app.get(url, params={'related_counts': False})
        relationships = res.json['data']['relationships']
        for relation in relationships.values():
            if relation == {}:
                continue
            link = relation['links'].values()[0]
            assert 'count' not in link['meta']

        #test_invalid_related_counts_value_raises_bad_request(self, app, url):
        res = app.get(url, params={'related_counts': 'fish'}, expect_errors=True)
        assert res.status_code == http.BAD_REQUEST

        #test_invalid_embed_value_raise_bad_request
        res = app.get(url, params={'embed': 'foo'}, expect_errors=True)
        assert res.status_code == http.BAD_REQUEST
        assert res.json['errors'][0]['detail'] == "The following fields are not embeddable: foo"

        #test_embed_does_not_remove_relationship
        res = app.get(url, params={'embed': 'root'})
        assert res.status_code == 200
        assert url in res.json['data']['relationships']['root']['links']['related']['href']

        #test_counts_included_in_children_field_with_children_related_counts_query_param
        res = app.get(url, params={'related_counts': 'children'})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if getattr(field, 'field', None):
                field = field.field
            link = relation['links'].values()[0]
            if (field.related_meta or {}).get('count') and key == 'children':
                assert 'count' in link['meta']
            else:
                assert 'count' not in link['meta']

        #test_counts_included_in_children_and_contributors_fields_with_field_csv_related_counts_query_param
        res = app.get(url, params={'related_counts': 'children,contributors'})
        relationships = res.json['data']['relationships']
        for key, relation in relationships.iteritems():
            if relation == {}:
                continue
            field = NodeSerializer._declared_fields[key]
            if getattr(field, 'field', None):
                field = field.field
            link = relation['links'].values()[0]
            if (field.related_meta or {}).get('count') and key == 'children' or key == 'contributors':
                assert 'count' in link['meta']
            else:
                assert 'count' not in link['meta']

        #test_error_when_requesting_related_counts_for_attribute_field
        res = app.get(url, params={'related_counts': 'title'}, expect_errors=True)
        assert res.status_code == http.BAD_REQUEST
        assert res.json['errors'][0]['detail'] == "Acceptable values for the related_counts query param are 'true', 'false', or any of the relationship fields; got 'title'"


@pytest.mark.django_db
class TestRelationshipField:

    # We need a Serializer to test the Relationship field (needs context)
    class BasicNodeSerializer(JSONAPISerializer):

        parent = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<_id>'}
        )

        parent_with_meta = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<_id>'},
            related_meta={'count': 'get_count', 'extra': 'get_extra'},
        )

        self_and_related_field = RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<_id>'},
            self_view='nodes:node-contributors',
            self_view_kwargs={'node_id': '<_id>'},
        )

        two_url_kwargs = RelationshipField(
            # fake url, for testing purposes
            related_view='nodes:node-pointer-detail',
            related_view_kwargs={'node_id': '<_id>', 'node_link_id': '<_id>'},
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
                'node_id': '<registered_from._id>'
            }
        )

        field_with_filters = base_serializers.RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<_id>'},
            filter={'target': 'hello', 'woop': 'yea'}
        )

        class Meta:
            type_ = 'nodes'

        def get_count(self, obj):
            return 1

        def get_extra(self, obj):
            return 'foo'

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def component(self, project):
        return NodeFactory(parent=project)

    @pytest.fixture()
    def drf_request(self):
        return make_drf_request_with_version(version='2.0')

    # TODO: Expand tests

    def test_base_node_serializers(self, drf_request, component):

        data = self.BasicNodeSerializer(component, context={'request': drf_request}).data['data']

        #Regression test for https://openscience.atlassian.net/browse/OSF-4832
        #test_serializing_meta

        meta = data['relationships']['parent_with_meta']['links']['related']['meta']
        assert 'count' not in meta
        assert 'extra' in meta
        assert meta['extra'] == 'foo'

        #test_self_and_related_fields
        relationship_field = data['relationships']['self_and_related_field']['links']
        assert '/v2/nodes/{}/contributors/'.format(component._id) in relationship_field['self']['href']
        assert '/v2/nodes/{}/'.format(component._id) in relationship_field['related']['href']

        #test_field_with_two_kwargs
        field = data['relationships']['two_url_kwargs']['links']
        assert '/v2/nodes/{}/node_links/{}/'.format(component._id, component._id) in field['related']['href']

        #test_field_with_two_filters
        field = data['relationships']['field_with_filters']['links']
        assert urllib.quote('filter[target]=hello', safe='?=') in field['related']['href']
        assert urllib.quote('filter[woop]=yea', safe='?=') in field['related']['href']

        #test_field_with_non_attribute
        field = data['relationships']['not_attribute_on_target']['links']
        assert '/v2/nodes/{}/children/'.format('12345') in field['related']['href']

        #test_field_with_callable_related_attrs
        assert 'registered_from' not in data['relationships']

        registration = RegistrationFactory(project=component)
        data = self.BasicNodeSerializer(registration, context={'request': drf_request}).data['data']
        field = data['relationships']['registered_from']['links']
        assert '/v2/nodes/{}/'.format(component._id) in field['related']['href']

@pytest.mark.django_db
class TestShowIfVersion:

    def test_show_on_bad_or_allowed_versions(self):
        node = NodeFactory()
        registration = RegistrationFactory()

        #test_node_links_allowed_version_node_serializer
        req = make_drf_request_with_version(version='2.0')
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert 'node_links' in data['relationships']

        #test_node_links_bad_version_node_serializer
        req = make_drf_request_with_version(version='2.1')
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert 'node_links' not in data['relationships']

        #test_node_links_allowed_version_registration_serializer
        req = make_drf_request_with_version(version='2.0')
        data = RegistrationSerializer(registration, context={'request': req}).data['data']
        assert 'node_links' in data['attributes']

        #test_node_links_bad_version_registration_serializer
        req = make_drf_request_with_version(version='2.1')
        data = RegistrationSerializer(registration, context={'request': req}).data['data']
        assert 'node_links' not in data['attributes']

@pytest.mark.django_db
class TestDateByVersion:

    def test_date_by_version(self):

        node = NodeFactory()
        old_date = datetime.utcnow()   # naive dates before django-osf
        old_date_without_microseconds = old_date.replace(microsecond=0)
        new_date = datetime.utcnow().replace(tzinfo=utc)  # non-naive after django-osf
        new_date_without_microseconds = new_date.replace(microsecond=0)
        old_format = '%Y-%m-%dT%H:%M:%S.%f'
        old_format_without_microseconds = '%Y-%m-%dT%H:%M:%S'
        new_format = '%Y-%m-%dT%H:%M:%S.%fZ'

        #test_old_date_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        setattr(node, 'date_modified', old_date)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert datetime.strftime(old_date, old_format) == data['attributes']['date_modified']

        #test_old_date_without_microseconds_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        setattr(node, 'date_modified', old_date_without_microseconds)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert (
            datetime.strftime(old_date_without_microseconds, old_format_without_microseconds) ==
            data['attributes']['date_modified'])

        #test_old_date_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        setattr(node, 'date_modified', old_date)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert datetime.strftime(old_date, new_format) == data['attributes']['date_modified']

        #test_old_date_without_microseconds_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        setattr(node, 'date_modified', old_date_without_microseconds)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert (
            datetime.strftime(old_date_without_microseconds, new_format) ==
            data['attributes']['date_modified'])

        #test_new_date_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        setattr(node, 'date_modified', new_date)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert datetime.strftime(new_date, old_format) == data['attributes']['date_modified']

        #test_new_date_without_microseconds_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        setattr(node, 'date_modified', new_date_without_microseconds)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert (
            datetime.strftime(new_date_without_microseconds, old_format_without_microseconds) ==
            data['attributes']['date_modified'])

        #test_new_date_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        setattr(node, 'date_modified', new_date)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert datetime.strftime(new_date, new_format) == data['attributes']['date_modified']

        #test_new_date_without_microseconds_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        setattr(node, 'date_modified', new_date_without_microseconds)
        data = NodeSerializer(node, context={'request': req}).data['data']
        assert (
            datetime.strftime(new_date_without_microseconds, new_format) ==
            data['attributes']['date_modified'])
