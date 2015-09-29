import re
import functools
import operator
from dateutil import parser as date_parser

from modularodm import Q
from rest_framework.filters import OrderingFilter
from rest_framework import serializers as ser

from api.base.exceptions import (
    InvalidFilterError,
    InvalidFilterOperator,
    InvalidFilterComparisonType,
    InvalidFilterMatchType,
    InvalidFilterValue
)
from api.base import utils

class ODMOrderingFilter(OrderingFilter):
    """Adaptation of rest_framework.filters.OrderingFilter to work with modular-odm."""

    # override
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            return queryset.sort(*ordering)
        return queryset


class FilterMixin(object):
    """ View mixin with helper functions for filtering. """

    QUERY_PATTERN = re.compile(r'^filter\[(?P<field>\w+)\](\[(?P<op>\w+)\])?$')
    COMPARISON_OPERATORS = ('gt', 'gte', 'lt', 'lte', 'eq')
    COMPARABLE_FIELDS = (ser.DateField, ser.DateTimeField, ser.DecimalField, ser.IntegerField)
    MATCH_OPERATORS = ('contains', 'icontains')
    MATCHABLE_FIELDS = (ser.CharField, ser.ListField)
    DEFAULT_OPERATOR = 'eq'
    DEFAULT_OPERATOR_OVERRIDES = {
        ser.CharField: 'icontains',
        ser.ListField: 'contains',
    }

    def __init__(self, *args, **kwargs):
        super(FilterMixin, self).__init__(*args, **kwargs)
        if not self.serializer_class:
            raise NotImplementedError()

    def _get_default_operator(self, field):
        return self.DEFAULT_OPERATOR_OVERRIDES.get(type(field), self.DEFAULT_OPERATOR)

    def parse_query_params(self, query_params):
        """Maps query params to a dict useable for filtering
        :param dict query_params:
        :raises InvalidFilterError: If the filter field is not valid
        :raises InvalidFilterComparisonType: If the query contains comparisons against non-date or non-numeric fields
        :raises InvalidFilterOperator: If the filter operator is not a member of self.COMPARISON_OPERATORS
        :raises InvalidFilterError: If the filter string is otherwise malformed
        :return dict: of the format {
            <resolved_field_name>: {
                'op': <comparison_operator>,
                'value': <resolved_value>
            }
        }
        """
        fields = {}
        for key, value in query_params.iteritems():
            if self.QUERY_PATTERN.match(key):
                match = self.QUERY_PATTERN.match(key)
                if match:
                    field_name = match.groupdict().get('field').strip()
                    if field_name not in self.serializer_class._declared_fields:
                        raise InvalidFilterError(detail="'{0}' is not a valid field for this endpoint".format(field_name))
                    if field_name not in self.serializer_class.filterable_fields:
                        raise InvalidFilterError
                    field = self.serializer_class._declared_fields[field_name]
                    op = match.groupdict().get('op') or self._get_default_operator(field)
                    if op not in set(self.MATCH_OPERATORS + self.COMPARABLE_FIELDS + (self.DEFAULT_OPERATOR, )):
                        raise InvalidFilterOperator(value=op)
                    if op in self.COMPARISON_OPERATORS:
                        if type(field) not in self.COMPARABLE_FIELDS:
                            raise InvalidFilterComparisonType(parameter=field_name)
                    if op in self.MATCH_OPERATORS:
                        if type(field) not in self.MATCHABLE_FIELDS:
                            raise InvalidFilterMatchType(parameter=field_name)
                    field_name = self.convert_key(field_name, field)
                    if field_name not in fields:
                        fields[field_name] = []
                    fields[field_name].append({
                        'op': op,
                        'value': self.convert_value(value, field)
                    })
                else:
                    raise InvalidFilterError
        return fields

    def convert_key(self, field_name, field):
        """Used so that that queries on fields with the souce attribute set will work
        :param basestring field_name: text representation of the field name
        :param rest_framework.fields.Field field: Field instance
        """
        return field.source or field_name

    def convert_value(self, value, field):
        """Used to convert string values from query params to bools and dates when necessary
        :param basestring value: value to be resolved
        :param rest_framework.fields.Field field: Field instance
        """
        field_type = type(field)
        value = value.strip()
        if field_type == ser.BooleanField:
            if utils.is_truthy(value):
                return True
            elif utils.is_falsy(value):
                return False
            else:
                raise InvalidFilterValue(
                    value=value,
                    field_type='bool'
                )
        elif field_type == ser.DateTimeField or field_type == ser.DateField:
            try:
                return date_parser.parse(value)
            except ValueError:
                raise InvalidFilterValue(
                    value=value,
                    field_type='date'
                )
        else:
            return value


class ODMFilterMixin(FilterMixin):
    """View mixin that adds a get_query_from_request method which converts query params
    of the form `filter[field_name]=value` into an ODM Query object.

    Subclasses must define `get_default_odm_query()`.

    Serializers that want to restrict which fields are used for filtering need to have a variable called
    filterable_fields which is a frozenset of strings representing the field names as they appear in the serialization.
    """

    # TODO Handle simple and complex non-standard fields
    field_comparison_operators = {
        ser.CharField: 'icontains',
        ser.ListField: 'contains',
    }

    def __init__(self, *args, **kwargs):
        super(FilterMixin, self).__init__(*args, **kwargs)
        if not self.serializer_class:
            raise NotImplementedError()

    def get_default_odm_query(self):
        """Return the default MODM query for the result set.

        NOTE: If the client provides additional filters in query params, the filters
        will intersected with this query.
        """
        raise NotImplementedError('Must define get_default_odm_query')

    def get_query_from_request(self):
        param_query = self.query_params_to_odm_query(self.request.QUERY_PARAMS)
        default_query = self.get_default_odm_query()

        if param_query:
            query = param_query & default_query
        else:
            query = default_query

        return query

    def query_params_to_odm_query(self, query_params):
        """Convert query params to a modularodm Query object."""

        filters = self.parse_query_params(query_params)
        if filters:
            query_parts = []
            for field_name, params in filters.iteritems():
                for group in params:
                    query = Q(field_name, group['op'], group['value'])
                    query_parts.append(query)
            try:
                query = functools.reduce(operator.and_, query_parts)
            except TypeError:
                query = None
        else:
            query = None
        return query


class ListFilterMixin(FilterMixin):
    """View mixin that adds a get_queryset_from_request method which uses query params
    of the form `filter[field_name]=value` to filter a list of objects.

    Subclasses must define `get_default_queryset()`.

    Serializers that want to restrict which fields are used for filtering need to have a variable called
    filterable_fields which is a frozenset of strings representing the field names as they appear in the serialization.
    """
    FILTERS = {
        'eq': operator.eq,
        'lt': operator.lt,
        'lte': operator.le,
        'gt': operator.gt,
        'gte': operator.ge
    }

    def __init__(self, *args, **kwargs):
        super(FilterMixin, self).__init__(*args, **kwargs)
        if not self.serializer_class:
            raise NotImplementedError()

    def get_default_queryset(self):
        raise NotImplementedError('Must define get_default_queryset')

    def get_queryset_from_request(self):
        default_queryset = self.get_default_queryset()
        if self.request.QUERY_PARAMS:
            param_queryset = self.param_queryset(self.request.QUERY_PARAMS, default_queryset)
            return param_queryset
        else:
            return default_queryset

    def param_queryset(self, query_params, default_queryset):
        """filters default queryset based on query parameters"""
        filters = self.parse_query_params(query_params)
        queryset = set(default_queryset)
        if filters:
            for field_name, params in filters.iteritems():
                for group in params:
                    queryset = queryset.intersection(set(self.get_filtered_queryset(field_name, group, default_queryset)))
        return list(queryset)

    def get_filtered_queryset(self, field_name, params, default_queryset):
        """filters default queryset based on the serializer field type"""
        field = self.serializer_class._declared_fields[field_name]

        if isinstance(field, ser.SerializerMethodField):
            return_val = [
                item for item in default_queryset
                if self.FILTERS[params['op']](self.get_serializer_method(field_name)(item), params['value'])
            ]
        elif isinstance(field, ser.BooleanField):
            return_val = [
                item for item in default_queryset
                if self.FILTERS[params['op']](getattr(item, field_name, None), params['value'])
            ]
        elif isinstance(field, ser.CharField):
            return_val = [
                item for item in default_queryset
                if params['value'] in getattr(item, field_name, None).lower()
            ]
        else:
            return_val = [
                item for item in default_queryset
                if self.FILTERS[params['op']](getattr(item, field_name, None), params['value'])
            ]

        return return_val

    def get_serializer_method(self, field_name):
        """
        :param field_name: The name of a SerializerMethodField
        :return: The function attached to the SerializerMethodField to get its value
        """
        serializer = self.get_serializer()
        serializer_method_name = 'get_' + field_name
        return getattr(serializer, serializer_method_name)
