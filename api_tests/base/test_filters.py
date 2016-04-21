# -*- coding: utf-8 -*-
import datetime
import re
from dateutil import parser

import json

from nose.tools import *  # flake8: noqa

from rest_framework import serializers as ser

from tests.base import ApiTestCase

from api.base.filters import FilterMixin

from api.base.filters import ODMOrderingFilter

import api.base.filters as filters 

from rest_framework.test import force_authenticate

from api.base.exceptions import (
    InvalidFilterError,
    InvalidFilterOperator,
    InvalidFilterComparisonType,
    InvalidFilterMatchType,
)

class FakeSerializer(ser.Serializer):

    filterable_fields = ('string_field', 'list_field', 'date_field', 'int_field', 'bool_field')

    string_field = ser.CharField()
    list_field = ser.ListField()
    date_field = ser.DateField()
    datetime_field = ser.DateTimeField()
    int_field = ser.IntegerField()
    float_field = ser.FloatField()
    bool_field = ser.BooleanField(source='foobar')

class FakeView(FilterMixin):

    serializer_class = FakeSerializer


class TestFilterMixin(ApiTestCase):

    def setUp(self):
        super(TestFilterMixin, self).setUp()
        self.view = FakeView()

    def test_parse_query_params_default_operators(self):
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        assert_in('string_field', fields)
        assert_equal(fields['string_field'][0]['op'], 'icontains')
        
        assert_in('list_field', fields)
        assert_equal(fields['list_field'][0]['op'], 'contains')

        assert_in('int_field', fields)
        assert_equal(fields['int_field'][0]['op'], 'eq')

        assert_in('foobar', fields)
        assert_equal(fields['foobar'][0]['op'], 'eq')

    def test_parse_query_params_casts_values(self):
        query_params = {
            'filter[string_field]': 'foo',
            'filter[list_field]': 'bar',
            'filter[int_field]': '42',
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        assert_in('string_field', fields)
        assert_equal(fields['string_field'][0]['value'], 'foo')
        
        assert_in('list_field', fields)
        assert_equal(fields['list_field'][0]['value'], 'bar')

        assert_in('int_field', fields)
        assert_equal(fields['int_field'][0]['value'], 42)

        assert_in('foobar', fields)
        assert_equal(fields['foobar'][0]['value'], False)

    def test_parse_query_params_uses_field_source_attribute(self):
        query_params = {
            'filter[bool_field]': 'false',
        }

        fields = self.view.parse_query_params(query_params)
        assert_in('foobar', fields)
        assert_equal(fields['foobar'][0]['value'], False)
        assert_equal(fields['foobar'][0]['op'], 'eq')

    def test_parse_query_params_generalizes_dates(self):
        query_params = {
            'filter[date_field]': '2014-12-12'
        }

        fields = self.view.parse_query_params(query_params)
        start = parser.parse('2014-12-12')
        stop = start + datetime.timedelta(days=1)
        for match in fields['date_field']:
            if match['op'] == 'gte':
                assert_equal(match['value'], start)
            elif match['op'] == 'lt':
                assert_equal(match['value'], stop)
            else:
                self.fail()        

    def test_parse_query_params_comparable_field(self):
        query_params = {
            'filter[int_field][gt]': 42,
            'fitler[int_field][lte]': 9000
        }

        fields = self.view.parse_query_params(query_params)
        for match in fields['int_field']:
            if match['op'] == 'gt':
                assert_equal(match['value'], 42)
            elif match['op'] == 'lte':
                assert_equal(match['value'], 9000)
            else:
                self.fail()
        
    def test_parse_query_params_matchable_field(self):
        query_params = {
            'filter[string_field][contains]': 'foo',
            'filter[string_field][icontains]': 'bar'
        }
        fields = self.view.parse_query_params(query_params)
        for match in fields['string_field']:
            if match['op'] == 'contains':
                assert_equal(match['value'], 'foo')
            elif match['op'] == 'icontains':
                assert_equal(match['value'], 'bar')
            else:
                self.fail()

    def test_parse_query_params_raises_InvalidFilterError_bad_field(self):
        query_params = {
            'filter[fake]': 'foo'
        }
        with assert_raises(InvalidFilterError):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterComparisonType(self):
        query_params = {
            'filter[string_field][gt]': 'foo'
        }
        with assert_raises(InvalidFilterComparisonType):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterMatchType(self):
        query_params = {
            'filter[date_field][icontains]': '2015'
        }
        with assert_raises(InvalidFilterMatchType):
            self.view.parse_query_params(query_params)

    def test_parse_query_params_raises_InvalidFilterOperator(self):
        query_params = {
            'filter[int_field][bar]': 42
        }
        with assert_raises(InvalidFilterOperator):
            self.view.parse_query_params(query_params)

    def test_InvalidFilterOperator_parameterizes_valid_operators(self):
        query_params = {
            'filter[int_field][bar]': 42
        }
        try:
            self.view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(r'one of (?P<ops>.+)\.$', err.detail).groupdict()['ops']
            assert_equal(ops, "gt, gte, lt, lte, eq, ne")

        query_params = {
            'filter[string_field][bar]': 'foo'
        }
        try:
            self.view.parse_query_params(query_params)
        except InvalidFilterOperator as err:
            ops = re.search(r'one of (?P<ops>.+)\.$', err.detail).groupdict()['ops']
            assert_equal(ops, "contains, icontains, eq, ne")


    def test_parse_query_params_supports_multiple_filters(self):
        query_params = {
            'filter[string_field]': 'foo',
            'filter[string_field]': 'bar',
        }

        fields = self.view.parse_query_params(query_params)
        assert_in('string_field', fields)
        for match in fields['string_field']:
            assert_in(match['value'], ('foo', 'bar'))

    def test_convert_value_bool(self):
        value = 'true'
        field = FakeSerializer._declared_fields['bool_field']
        value = self.view.convert_value(value, field)
        assert_true(isinstance(value, bool))
        assert_true(value)

    def test_convert_value_date(self):
        value = '2014-12-12'        
        field = FakeSerializer._declared_fields['date_field']
        value = self.view.convert_value(value, field)
        assert_true(isinstance(value, datetime.datetime))
        assert_equal(value, parser.parse('2014-12-12'))

    def test_convert_value_int(self):
        value = '9000'
        field = FakeSerializer._declared_fields['int_field']
        value = self.view.convert_value(value, field)
        assert_equal(value, 9000)

    def test_convert_value_float(self):
        value = '42'
        orig_type = type(value)
        field = FakeSerializer._declared_fields['float_field']
        value = self.view.convert_value(value, field)
        assert_equal(value, 42.0)



class TestODMOrderingFilter(ApiTestCase):
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
        query_to_be_sorted = [self.query(x) for x in 'NewProj Zip Proj Activity'.split()]
        sorted_query = sorted(query_to_be_sorted, cmp=filters.sort_multiple(['title']))
        sorted_output = [str(i) for i in sorted_query]
        assert_equal((sorted_output) , ['Activity', 'NewProj', 'Proj', 'Zip'])


    def test_filter_queryset_forward_duplicate(self):
        query_to_be_sorted = [self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(query_to_be_sorted, cmp=filters.sort_multiple(['-title']))
        sorted_output = [str(i) for i in sorted_query]
        assert_equal((sorted_output) , ['Activity', 'Activity', 'NewProj', 'Zip'])


    def test_filter_queryset_reverse(self):
        query_to_be_sorted = [self.query(x) for x in 'NewProj Zip Proj Activity'.split()]
        sorted_query = sorted(query_to_be_sorted, cmp=filters.sort_multiple(['-title']))
        sorted_output = [str(i) for i in sorted_query]
        assert_equal((sorted_output) , ['Zip', 'Proj', 'NewProj', 'Activity'])
    
    def test_filter_queryset_reverse_duplicate(self):
        query_to_be_sorted = [self.query(x) for x in 'NewProj Activity Zip Activity'.split()]
        sorted_query = sorted(query_to_be_sorted, cmp=filters.sort_multiple(['-title']))
        sorted_output = [str(i) for i in sorted_query]
        assert_equal((sorted_output) , ['Zip', 'NewProj', 'Activity', 'Activity'])

    def test_filter_queryset_handles_multiple_fields(self):
        objs = [self.query_with_num(title='NewProj', number=10),
                self.query_with_num(title='Zip', number=20),
                self.query_with_num(title='Activity', number=30),
                self.query_with_num(title='Activity', number=40)]
        actual = [x.number for x in sorted(objs, cmp=filters.sort_multiple(['title', '-number']))]
        assert_equal(actual, [40, 30, 10, 20])

