import re
import functools

from modularodm import Q
from rest_framework.filters import OrderingFilter
from rest_framework import serializers as ser


class ODMOrderingFilter(OrderingFilter):
    """Adaptation of rest_framework.filters.OrderingFilter to work with modular-odm."""

    # override
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if ordering:
            return queryset.sort(*ordering)
        return queryset

query_pattern = re.compile(r'filter\[\s*(?P<field>\S*)\s*\]\s*')


def query_params_to_fields(query_params):
    return {
        query_pattern.match(key).groupdict()['field']: value
        for key, value in query_params.items()
        if query_pattern.match(key)
    }


# Used to make intersection "reduce-able"
def intersect(x, y):
    return x & y


class FilterMixin(object):
    """ View mixin with helper functions for filtering. """

    TRUTHY = set(['true', 'True', 1, '1'])
    FALSY = set(['false', 'False', 0, '0'])
    DEFAULT_OPERATOR = 'eq'

    def is_filterable_field(self, key):
        try:
            return key.strip() in self.serializer_class.filterable_fields
        except AttributeError:
            return key.strip() in self.serializer_class._declared_fields

    # Used so that that queries by _id will work
    def convert_key(self, key):
        key = key.strip()
        if self.serializer_class._declared_fields[key].source:
            return self.serializer_class._declared_fields[key].source
        return key

    # Used to convert string values from query params to Python booleans when necessary
    def convert_value(self, value):
        value = value.strip()
        if value in self.TRUTHY:
            return True
        elif value in self.FALSY:
            return False
        # Convert me to current user's pk
        elif value == 'me' and not self.request.user.is_anonymous():
            return self.request.user.pk
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

    # For the field_comparison_operators, instances can be a class or a tuple of classes
    field_comparison_operators = [
        {
            'field_type': ser.CharField,
            'comparison_operator': 'icontains'
        },
        {
            'field_type': ser.ListField,
            'comparison_operator': 'in'
        }
    ]

    def get_comparison_operator(self, key):

        for operator in self.field_comparison_operators:
            if isinstance(self.serializer_class._declared_fields[key], operator['field_type']):
                return operator['comparison_operator']

        return self.DEFAULT_OPERATOR

    def get_default_odm_query(self):
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

        fields_dict = query_params_to_fields(query_params)
        if fields_dict:
            query_parts = [
                Q(self.convert_key(key=key), self.get_comparison_operator(key=key), self.convert_value(value=value))
                for key, value in fields_dict.items() if self.is_filterable_field(key=key)
            ]
            # TODO Ensure that if you try to filter on an invalid field, it returns a useful error. Fix related test.
            try:
                query = functools.reduce(intersect, query_parts)
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
        fields_dict = query_params_to_fields(query_params)
        if fields_dict:
            for field_name, value in fields_dict.items():
                if self.is_filterable_field(key=field_name):
                    if isinstance(self.serializer_class._declared_fields[field_name], ser.SerializerMethodField):
                        return self.get_serializer_field_value(field_name, value, default_queryset)
                    elif isinstance(self.serializer_class._declared_fields[field_name], ser.BooleanField):
                        return [item for item in default_queryset if item.get('key', None) == value]
                    else:
                        return [item for item in default_queryset if value in item.get('key', None)]

    def get_serializer_field_value(self, key, value, default_queryset):
        serializer = self.get_serializer()
        serializer_function = {
            'bibliographic': serializer.get_bibliographic
        }
        return [item for item in default_queryset if serializer_function[key](item) == self.convert_value(value)]
