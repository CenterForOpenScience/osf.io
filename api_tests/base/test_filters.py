import datetime
import re
import pytest
import pytz

from dateutil import parser
from django.utils import timezone

from rest_framework import generics
from rest_framework import serializers as ser

from unittest import TestCase

from tests.base import ApiTestCase

from api.base.filters import ListFilterMixin
import api.base.filters as filters
from api.base.exceptions import (
    InvalidFilterError,
    InvalidFilterOperator,
    InvalidFilterComparisonType,
    InvalidFilterMatchType,
)
from osf_tests.factories import (
    NodeFactory,
    AuthUserFactory,
)
from api.base.settings.defaults import API_BASE
from api.base.serializers import RelationshipField

from functools import cmp_to_key

class FakeSerializer(ser.Serializer):

    filterable_fields = (
        'id',
        'string_field',
        'second_string_field',
        'list_field',
        'date_field',
        'int_field',
        'bool_field',
        'relationship_field'
    )

    id = ser.CharField()
    string_field = ser.CharField()
    second_string_field = ser.CharField()
    list_field = ser.ListField()
    date_field = ser.DateField()
    datetime_field = ser.DateTimeField()
    int_field = ser.IntegerField()
    float_field = ser.FloatField()
    bool_field = ser.BooleanField(source='foobar')
    relationship_field = RelationshipField(
        related_view='fake', related_view_kwargs={}
    )


class FakeRecord:

    def __init__(
            self,
            _id=None,
            string_field='foo',
            second_string_field='bar',
            list_field=None,
            date_field=timezone.now(),
            datetime_field=timezone.now(),
            int_field=42,
            float_field=41.99999,
            foobar=True
    ):
        self._id = _id
        self.string_field = string_field
        self.second_string_field = second_string_field
        self.list_field = list_field or [1, 2, 3]
        self.date_field = date_field
        self.datetime_field = datetime_field
        self.int_field = int_field
        self.float_field = float_field
        # bool_field in serializer corresponds to foobar in model
        self.foobar = foobar


class FakeListView(ListFilterMixin, generics.GenericAPIView):
    serializer_class = FakeSerializer

    def get_serializer_context(self):
        return {}


class TestFilterMixin(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.view = FakeListView()

    def test_parse_query_params_default_operators(self):
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        self.assertIn('string_field', fields['filter[string_field]'])
        self.assertEqual(
            fields['filter[string_field]']['string_field']['op'],
            'icontains'
        )

        self.assertIn('list_field', fields['filter[list_field]'])
        self.assertEqual(
            fields['filter[list_field]']['list_field']['op'],
            'contains'
        )

        self.assertIn('int_field', fields['filter[int_field]'])
        self.assertEqual(fields['filter[int_field]']['int_field']['op'], 'eq')

        self.assertIn('bool_field', fields['filter[bool_field]'])
        self.assertEqual(fields['filter[bool_field]']['bool_field']['op'], 'eq')

    def test_parse_query_params_casts_values(self):
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        self.assertIn('string_field', fields['filter[string_field]'])
        self.assertEqual(
            fields['filter[string_field]']['string_field']['value'],
            'foo'
        )

        self.assertIn('list_field', fields['filter[list_field]'])
        self.assertEqual(
            fields['filter[list_field]']['list_field']['value'],
            'bar'
        )

        self.assertIn('int_field', fields['filter[int_field]'])
        self.assertEqual(fields['filter[int_field]']['int_field']['value'], 42)

        self.assertIn('bool_field', fields.get('filter[bool_field]'))
        self.assertEqual(
            fields['filter[bool_field]']['bool_field']['value'],
            False
        )

    def test_parse_query_params_uses_field_source_attribute(self):
        query_params = {
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        parsed_field = fields['filter[bool_field]']['bool_field']
        self.assertEqual(parsed_field['source_field_name'], 'foobar')
        self.assertEqual(parsed_field['value'], False)
        self.assertEqual(parsed_field['op'], 'eq')

    def test_parse_query_params_generalizes_dates(self):
        query_params = {
            'filter[date_field]': '2014-12-12'
        }

        fields = self.view.parse_query_params(query_params)
        start = parser.parse('2014-12-12').replace(tzinfo=pytz.utc)
        stop = start + datetime.timedelta(days=1)
        for key, field_name in fields.items():
            for match in field_name['date_field']:
                if match['op'] == 'gte':
                    self.assertEqual(match['value'], start)
                elif match['op'] == 'lt':
                    self.assertEqual(match['value'], stop)
                else:
                    self.fail()

    def test_parse_query_params_comparable_field(self):
        query_params = {
            'filter[int_field][gt]': 42,
            'filter[int_field][lte]': 9000
        }
        fields = self.view.parse_query_params(query_params)
        for key, field_name in fields.items():
            if field_name['int_field']['op'] == 'gt':
                self.assertEqual(field_name['int_field']['value'], 42)
            elif field_name['int_field']['op'] == 'lte':
                self.assertEqual(field_name['int_field']['value'], 9000)
            else:
                self.fail()

    def test_parse_query_params_matchable_field(self):
        query_params = {
            'filter[string_field][contains]': 'foo',
            'filter[string_field][icontains]': 'bar'
        }
        fields = self.view.parse_query_params(query_params)
        for key, field_name in fields.items():
            if field_name['string_field']['op'] == 'contains':
                self.assertEqual(field_name['string_field']['value'], 'foo')
            elif field_name['string_field']['op'] == 'icontains':
                self.assertEqual(field_name['string_field']['value'], 'bar')
            else:
                self.fail()

    def test_parse_query_params_raises_InvalidFilterError_bad_field(self):
        query_params = {
            'filter[fake]': 'foo'
        }
        with self.assertRaises(InvalidFilterError):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterComparisonType(self):
        query_params = {
            'filter[string_field][gt]': 'foo'
        }
        with self.assertRaises(InvalidFilterComparisonType):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterMatchType(self):
        query_params = {
            'filter[date_field][icontains]': '2015'
        }
        with self.assertRaises(InvalidFilterMatchType):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterOperator(self):
        query_params = {
            'filter[int_field][bar]': 42
        }
        with self.assertRaises(InvalidFilterOperator):
            self.view.parse_query_params(query_params)

    def test_InvalidFilterOperator_parameterizes_valid_operators(self):
        query_params = {
            'filter[int_field][bar]': 42
        }
        try:
            self.view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(
                r'one of (?P<ops>.+)\.$',
                err.detail
            ).groupdict()['ops']
            self.assertEqual(ops, 'gt, gte, lt, lte, eq, ne')

        query_params = {
            'filter[string_field][bar]': 'foo'
        }
        try:
            self.view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(
                r'one of (?P<ops>.+)\.$',
                err.detail
            ).groupdict()['ops']
            self.assertEqual(ops, 'contains, icontains, eq, ne')

    def test_parse_query_params_supports_multiple_filters(self):
        """
        # Commented out because broken and can't be ignored with flake noga
        query_params = {
            'filter[string_field]': 'foo',
            'filter[string_field]': 'bar',
        }
        # FIXME: This test may only be checking one field
        fields = self.view.parse_query_params(query_params)
        self.assertIn('string_field', fields.get('filter[string_field]'))
        for key, field_name in fields.items():
            self.assertIn(field_name['string_field']['value'], ('foo', 'bar'))
        """
    def test_convert_value_bool(self):
        value = 'true'
        field = FakeSerializer._declared_fields['bool_field']
        value = self.view.convert_value(value, field)
        self.assertTrue(isinstance(value, bool))
        self.assertTrue(value)

    def test_convert_value_date(self):
        value = '2014-12-12'
        field = FakeSerializer._declared_fields['date_field']
        value = self.view.convert_value(value, field)
        self.assertTrue(isinstance(value, datetime.datetime))
        self.assertEqual(
            value,
            parser.parse('2014-12-12').replace(tzinfo=pytz.utc)
        )

    def test_convert_value_int(self):
        value = '9000'
        field = FakeSerializer._declared_fields['int_field']
        value = self.view.convert_value(value, field)
        self.assertEqual(value, 9000)

    def test_convert_value_float(self):
        value = '42'
        field = FakeSerializer._declared_fields['float_field']
        value = self.view.convert_value(value, field)
        self.assertEqual(value, 42.0)

    def test_convert_value_null_for_list(self):
        value = 'null'
        field = FakeSerializer._declared_fields['list_field']
        value = self.view.convert_value(value, field)
        self.assertEqual(value, [])

    def test_multiple_filter_params_bad_filter(self):
        query_params = {
            'filter[string_field, not_a_field]': 'test'
        }
        with self.assertRaises(InvalidFilterError):
            self.view.parse_query_params(query_params)

    def test_bad_filter_operator(self):
        query_params = {
            'filter[relationship_field][invalid]': 'false',
        }
        with self.assertRaises(InvalidFilterOperator):
            self.view.parse_query_params(query_params)


class TestListFilterMixin(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.view = FakeListView()

    def test_get_filtered_queryset_for_list_field_converts_to_lowercase(self):
        field_name = 'list_field'
        params = {
            'value': 'FOO',
            'source_field_name': field_name
        }
        default_queryset = [
            FakeRecord(_id=1, list_field=['fOO', 'Foo', 'Bar', 'baR']),
            FakeRecord(_id=2, list_field=['Foo', 'Bax']),
            FakeRecord(_id=3, list_field=['Bar', 'baR', 'bat'])
        ]
        filtered = self.view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            self.assertNotEqual(record._id, 3)
        for id in (1, 2):
            self.assertIn(id, [f._id for f in filtered])

    def test_get_filtered_queryset_for_list_respects_special_case_of_ids_being_list(
            self):
        field_name = 'bool_field'
        params = {
            'value': True,
            'op': 'eq',
            'source_field_name': 'foobar'
        }
        default_queryset = [
            FakeRecord(_id=1, foobar=True),
            FakeRecord(_id=2, foobar=True),
            FakeRecord(_id=3, foobar=False)
        ]
        filtered = self.view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            self.assertNotEqual(record._id, 3)
        for id in (1, 2):
            self.assertIn(id, [f._id for f in filtered])

    def test_get_filtered_queryset_for_list_respects_id_always_being_list(
            self):
        field_name = 'id'
        params = {
            'value': '2',
            'op': 'in',
            'source_field_name': '_id'
        }
        default_queryset = [
            FakeRecord(_id='1', foobar=True),
            FakeRecord(_id='2', foobar=True),
            FakeRecord(_id='3', foobar=False)
        ]
        filtered = self.view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            self.assertEqual(record._id, '2')
        for id in ('1', '3'):
            self.assertNotIn(id, [f._id for f in filtered])

    def test_parse_query_params_uses_field_source_attribute(self):
        query_params = {
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        parsed_field = fields['filter[bool_field]']['bool_field']
        self.assertEqual(parsed_field['source_field_name'], 'foobar')
        self.assertEqual(parsed_field['value'], False)
        self.assertEqual(parsed_field['op'], 'eq')

@pytest.mark.django_db
class TestOSFOrderingFilter(ApiTestCase):
    class query:
        title = ' '

        def __init__(self, title):
            self.title = title

        def __str__(self):
            return self.title

    class query_with_num:
        title = ' '
        number = 0

        def __init__(self, title, number):
            self.title = title
            self.number = number

        def __str__(self):
            return self.title

    def test_filter_queryset_forward(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Zip Proj Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            key=cmp_to_key(filters.sort_multiple(['title']))
        )
        sorted_output = [str(i) for i in sorted_query]
        self.assertEqual(sorted_output, ['Activity', 'NewProj', 'Proj', 'Zip'])

    def test_filter_queryset_forward_duplicate(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            key=cmp_to_key(filters.sort_multiple(['title']))
        )
        sorted_output = [str(i) for i in sorted_query]
        self.assertEqual(sorted_output, ['Activity', 'Activity', 'NewProj', 'Zip'])

    def test_filter_queryset_reverse(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Zip Proj Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            key=cmp_to_key(filters.sort_multiple(['-title']))
        )
        sorted_output = [str(i) for i in sorted_query]
        self.assertEqual(sorted_output, ['Zip', 'Proj', 'NewProj', 'Activity'])

    def test_filter_queryset_reverse_duplicate(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            key=cmp_to_key(filters.sort_multiple(['-title']))
        )
        sorted_output = [str(i) for i in sorted_query]
        self.assertEqual(sorted_output, ['Zip', 'NewProj', 'Activity', 'Activity'])

    def test_filter_queryset_handles_multiple_fields(self):
        objs = [self.query_with_num(title='NewProj', number=10),
                self.query_with_num(title='Zip', number=20),
                self.query_with_num(title='Activity', number=30),
                self.query_with_num(title='Activity', number=40)]
        actual = [
            x.number for x in sorted(
                objs, key=cmp_to_key(filters.sort_multiple(['title', '-number']))
            )]
        self.assertEqual(actual, [40, 30, 10, 20])

    def get_node_sort_url(self, field, ascend=True):
        if not ascend:
            field = '-' + field
        return f'/{API_BASE}nodes/?sort={field}'

    def get_multi_field_sort_url(self, field, node_id, ascend=True):
        if not ascend:
            field = '-' + field
        return f'/{API_BASE}nodes/{node_id}/addons/?sort={field}'

    def test_sort_by_serializer_field(self):
        user = AuthUserFactory()
        NodeFactory(creator=user)
        NodeFactory(creator=user)

        # Ensuring that sorting by the serializer field returns the same result
        # as using the source field
        res_created = self.app.get(self.get_node_sort_url('created'), auth=user.auth)
        res_date_created = self.app.get(self.get_node_sort_url('date_created'), auth=user.auth)
        assert res_created.status_code == 200
        assert res_created.json['data'] == res_date_created.json['data']
        assert res_created.json['data'][0]['id'] == res_date_created.json['data'][0]['id']
        assert res_created.json['data'][1]['id'] == res_date_created.json['data'][1]['id']

        # Testing both are capable of using the inverse sort sign '-'
        res_created = self.app.get(self.get_node_sort_url('created', False), auth=user.auth)
        res_date_created = self.app.get(self.get_node_sort_url('date_created', False), auth=user.auth)
        assert res_created.status_code == 200
        assert res_created.json['data'] == res_date_created.json['data']
        assert res_created.json['data'][1]['id'] == res_date_created.json['data'][1]['id']
        assert res_created.json['data'][0]['id'] == res_date_created.json['data'][0]['id']


class TestQueryPatternRegex(TestCase):

    def setUp(self):
        super().setUp()
        self.filter_regex = FakeListView.QUERY_PATTERN
        self.filter_fields = FakeListView.FILTER_FIELDS

    def test_single_field_filter(self):
        filter_str = 'filter[name]'
        match = self.filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(self.filter_fields, fields)
        self.assertEqual(fields, 'name')
        self.assertEqual(field_names[0], 'name')

    def test_double_field_filter(self):
        filter_str = 'filter[name,id]'
        match = self.filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(self.filter_fields, fields)
        self.assertEqual(fields, 'name,id')
        self.assertEqual(field_names[0], 'name')
        self.assertEqual(field_names[1], 'id')

    def test_multiple_field_filter(self):
        filter_str = 'filter[name,id,another,field,here]'
        match = self.filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(self.filter_fields, fields)
        self.assertEqual(fields, 'name,id,another,field,here')
        self.assertEquals(len(field_names), 5)

    def test_single_field_filter_end_comma(self):
        filter_str = 'filter[name,]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)

    def test_multiple_field_filter_end_comma(self):
        filter_str = 'filter[name,id,]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)

    def test_multiple_field_filter_with_spaces(self):
        filter_str = 'filter[name,  id]'
        match = self.filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(self.filter_fields, fields)
        self.assertEqual(fields, 'name,  id')
        self.assertEqual(field_names[0], 'name')
        self.assertEqual(field_names[1], 'id')

    def test_multiple_field_filter_with_blank_field(self):
        filter_str = 'filter[name,  ,  id]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)

    def test_multiple_field_filter_non_match(self):
        filter_str = 'filter[name; id]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)

    def test_single_field_filter_non_match(self):
        filter_str = 'fitler[name]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)

    def test_single_field_non_alphanumeric_character(self):
        filter_str = 'fitler[<name>]'
        match = self.filter_regex.match(filter_str)
        self.assertFalse(match)
