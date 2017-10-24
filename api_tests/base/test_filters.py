# -*- coding: utf-8 -*-
import datetime
import functools
import operator
import re

import pytz
import pytest
from dateutil import parser
from django.utils import timezone
from rest_framework import serializers as ser

from api.base.filters import ListFilterMixin
import api.base.filters as filters
from api.base.exceptions import (
    InvalidFilterError,
    InvalidFilterOperator,
    InvalidFilterComparisonType,
    InvalidFilterMatchType,
)
from api.base.serializers import RelationshipField


class FakeSerializer(ser.Serializer):

    filterable_fields = (
        'id', 'string_field', 'second_string_field', 'list_field',
        'date_field', 'int_field', 'bool_field', 'relationship_field')

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
        related_view='fake', related_view_kwargs={})


class FakeRecord(object):

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


class FakeListView(ListFilterMixin):

    serializer_class = FakeSerializer


@pytest.fixture()
def view():
    return FakeListView()


class TestFilterMixin:

    def test_parse_query_params(self, view):

        # test_parse_query_params_default_operators
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = view.parse_query_params(query_params)
        assert 'string_field' in fields['filter[string_field]']
        assert fields['filter[string_field]']['string_field']['op'] == 'icontains'

        assert 'list_field' in fields['filter[list_field]']
        assert fields['filter[list_field]']['list_field']['op'] == 'contains'

        assert 'int_field' in fields['filter[int_field]']
        assert fields['filter[int_field]']['int_field']['op'] == 'eq'

        assert 'bool_field' in fields['filter[bool_field]']
        assert fields['filter[bool_field]']['bool_field']['op'] == 'eq'

        # test_parse_query_params_casts_values
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = view.parse_query_params(query_params)
        assert 'string_field' in fields['filter[string_field]']
        assert fields['filter[string_field]']['string_field']['value'] == 'foo'

        assert 'list_field' in fields['filter[list_field]']
        assert fields['filter[list_field]']['list_field']['value'] == 'bar'

        assert 'int_field' in fields['filter[int_field]']
        assert fields['filter[int_field]']['int_field']['value'] == 42

        assert 'bool_field' in fields.get('filter[bool_field]')
        assert fields['filter[bool_field]']['bool_field']['value'] is False

        # test_parse_query_params_uses_field_source_attribute
        query_params = {
            'filter[bool_field]': 'false',
        }

        fields = view.parse_query_params(query_params)
        parsed_field = fields['filter[bool_field]']['bool_field']
        assert parsed_field['source_field_name'] == 'foobar'
        assert parsed_field['value'] is False
        assert parsed_field['op'] == 'eq'

        # test_parse_query_params_raises_InvalidFilterError_bad_field
        query_params = {
            'filter[fake]': 'foo'
        }
        with pytest.raises(InvalidFilterError):
            view.parse_query_params(query_params)

        # test_parse_query_params_raises_InvalidFilterComparisonType
        query_params = {
            'filter[string_field][gt]': 'foo'
        }
        with pytest.raises(InvalidFilterComparisonType):
            view.parse_query_params(query_params)

        # test_parse_query_params_raises_InvalidFilterMatchType
        query_params = {
            'filter[date_field][icontains]': '2015'
        }
        with pytest.raises(InvalidFilterMatchType):
            view.parse_query_params(query_params)

        # test_parse_query_params_raises_InvalidFilterOperator
        query_params = {
            'filter[int_field][bar]': 42
        }
        with pytest.raises(InvalidFilterOperator):
            view.parse_query_params(query_params)

        # test_InvalidFilterOperator_parameterizes_valid_operators
        query_params = {
            'filter[int_field][bar]': 42
        }
        try:
            view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(
                r'one of (?P<ops>.+)\.$',
                err.detail).groupdict()['ops']
            assert ops == "gt, gte, lt, lte, eq, ne"

        query_params = {
            'filter[string_field][bar]': 'foo'
        }
        try:
            view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(
                r'one of (?P<ops>.+)\.$',
                err.detail).groupdict()['ops']
            assert ops == "contains, icontains, eq, ne"

        # test_parse_query_params_supports_multiple_filters
        query_params = {
            'filter[string_field]': 'foo',
            'filter[string_field]': 'bar',
        }
        # FIXME: This test may only be checking one field
        fields = view.parse_query_params(query_params)
        assert 'string_field' in fields.get('filter[string_field]')
        for key, field_name in fields.iteritems():
            assert field_name['string_field']['value'] in ('foo', 'bar')

        # test_convert_value_bool
        value = 'true'
        field = FakeSerializer._declared_fields['bool_field']
        value = view.convert_value(value, field)
        assert isinstance(value, bool)
        assert value

        # test_convert_value_date
        value = '2014-12-12'
        field = FakeSerializer._declared_fields['date_field']
        value = view.convert_value(value, field)
        assert isinstance(value, datetime.datetime)
        assert value == parser.parse('2014-12-12').replace(tzinfo=pytz.utc)

        # test_convert_value_int
        value = '9000'
        field = FakeSerializer._declared_fields['int_field']
        value = view.convert_value(value, field)
        assert value == 9000

        # test_convert_value_float
        value = '42'
        orig_type = type(value)
        field = FakeSerializer._declared_fields['float_field']
        value = view.convert_value(value, field)
        assert value == 42.0

        # test_convert_value_null_for_list
        value = 'null'
        field = FakeSerializer._declared_fields['list_field']
        value = view.convert_value(value, field)
        assert value == []

        # test_multiple_filter_params_bad_filter
        query_params = {
            'filter[string_field, not_a_field]': 'test'
        }
        with pytest.raises(InvalidFilterError):
            view.parse_query_params(query_params)

        # test_bad_filter_operator
        query_params = {
            'filter[relationship_field][invalid]': 'false',
        }
        with pytest.raises(InvalidFilterOperator):
            view.parse_query_params(query_params)

    def test_parse_query_params_generalizes_dates(self, view):
        query_params = {
            'filter[date_field]': '2014-12-12'
        }

        fields = view.parse_query_params(query_params)
        start = parser.parse('2014-12-12').replace(tzinfo=pytz.utc)
        stop = start + datetime.timedelta(days=1)
        for key, field_name in fields.iteritems():
            for match in field_name['date_field']:
                if match['op'] == 'gte':
                    assert match['value'] == start
                elif match['op'] == 'lt':
                    assert match['value'] == stop
                else:
                    self.fail()

    def test_parse_query_params_comparable_field(self, view):
        query_params = {
            'filter[int_field][gt]': 42,
            'filter[int_field][lte]': 9000
        }
        fields = view.parse_query_params(query_params)
        for key, field_name in fields.iteritems():
            if field_name['int_field']['op'] == 'gt':
                assert field_name['int_field']['value'] == 42
            elif field_name['int_field']['op'] == 'lte':
                assert field_name['int_field']['value'] == 9000
            else:
                self.fail()

    def test_parse_query_params_matchable_field(self, view):
        query_params = {
            'filter[string_field][contains]': 'foo',
            'filter[string_field][icontains]': 'bar'
        }
        fields = view.parse_query_params(query_params)
        for key, field_name in fields.iteritems():
            if field_name['string_field']['op'] == 'contains':
                assert field_name['string_field']['value'] == 'foo'
            elif field_name['string_field']['op'] == 'icontains':
                assert field_name['string_field']['value'] == 'bar'
            else:
                self.fail()


@pytest.mark.django_db
class TestListFilterMixin:

    def test_get_filtered_queryset_for_list_field_converts_to_lowercase(
            self,
            view):
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
        filtered = view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            assert record._id != 3
        for id in (1, 2):
            assert id in [f._id for f in filtered]

    def test_get_filtered_queryset_for_list_respects_special_case_of_ids_being_list(
            self,
            view):
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
        filtered = view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            assert record._id != 3
        for id in (1, 2):
            assert id in [f._id for f in filtered]

    def test_get_filtered_queryset_for_list_respects_id_always_being_list(
            self,
            view):
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
        filtered = view.get_filtered_queryset(
            field_name, params, default_queryset)
        for record in filtered:
            assert record._id == '2'
        for id in ('1', '3'):
            assert id not in [f._id for f in filtered]

    def test_parse_query_params_uses_field_source_attribute(self, view):
        query_params = {
            'filter[bool_field]': 'false',
        }

        fields = view.parse_query_params(query_params)
        parsed_field = fields['filter[bool_field]']['bool_field']
        assert parsed_field['source_field_name'] == 'foobar'
        assert parsed_field['value'] is False
        assert parsed_field['op'] == 'eq'


class TestODMOrderingFilter:

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
            cmp=filters.sort_multiple(
                ['title']))
        sorted_output = [str(i) for i in sorted_query]
        assert sorted_output == ['Activity', 'NewProj', 'Proj', 'Zip']

    def test_filter_queryset_forward_duplicate(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            cmp=filters.sort_multiple(
                ['title']))
        sorted_output = [str(i) for i in sorted_query]
        assert sorted_output == ['Activity', 'Activity', 'NewProj', 'Zip']

    def test_filter_queryset_reverse(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Zip Proj Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            cmp=filters.sort_multiple(
                ['-title']))
        sorted_output = [str(i) for i in sorted_query]
        assert sorted_output == ['Zip', 'Proj', 'NewProj', 'Activity']

    def test_filter_queryset_reverse_duplicate(self):
        query_to_be_sorted = [
            self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(
            query_to_be_sorted,
            cmp=filters.sort_multiple(
                ['-title']))
        sorted_output = [str(i) for i in sorted_query]
        assert sorted_output == ['Zip', 'NewProj', 'Activity', 'Activity']

    def test_filter_queryset_handles_multiple_fields(self):
        objs = [self.query_with_num(title='NewProj', number=10),
                self.query_with_num(title='Zip', number=20),
                self.query_with_num(title='Activity', number=30),
                self.query_with_num(title='Activity', number=40)]
        actual = [x.number for x in sorted(
            objs, cmp=filters.sort_multiple(['title', '-number']))]
        assert actual == [40, 30, 10, 20]


class TestQueryPatternRegex:

    def test_query_pattern_regex(self):

        filter_regex = FakeListView.QUERY_PATTERN
        filter_fields = FakeListView.FILTER_FIELDS

        # test_single_field_filter
        filter_str = 'filter[name]'
        match = filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(filter_fields, fields)
        assert fields == 'name'
        assert field_names[0] == 'name'

        # test_double_field_filter
        filter_str = 'filter[name,id]'
        match = filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(filter_fields, fields)
        assert fields == 'name,id'
        assert field_names[0] == 'name'
        assert field_names[1] == 'id'

        # test_multiple_field_filter
        filter_str = 'filter[name,id,another,field,here]'
        match = filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(filter_fields, fields)
        assert fields == 'name,id,another,field,here'
        assert len(field_names) == 5

        # test_single_field_filter_end_comma
        filter_str = 'filter[name,]'
        match = filter_regex.match(filter_str)
        assert not match

        # test_multiple_field_filter_end_comma
        filter_str = 'filter[name,id,]'
        match = filter_regex.match(filter_str)
        assert not match

        # test_multiple_field_filter_with_spaces
        filter_str = 'filter[name,  id]'
        match = filter_regex.match(filter_str)
        fields = match.groupdict()['fields']
        field_names = re.findall(filter_fields, fields)
        assert fields == 'name,  id'
        assert field_names[0] == 'name'
        assert field_names[1] == 'id'

        # test_multiple_field_filter_with_blank_field
        filter_str = 'filter[name,  ,  id]'
        match = filter_regex.match(filter_str)
        assert not match

        # test_multiple_field_filter_non_match
        filter_str = 'filter[name; id]'
        match = filter_regex.match(filter_str)
        assert not match

        # test_single_field_filter_non_match
        filter_str = 'fitler[name]'
        match = filter_regex.match(filter_str)
        assert not match

        # test_single_field_non_alphanumeric_character
        filter_str = 'fitler[<name>]'
        match = filter_regex.match(filter_str)
        assert not match
