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


class ODMFilterMixin(object):
    """View mixin that adds a get_query_from_request method which converts query params
    of the form `filter[field_name]=value` into an ODM Query object.

    Subclasses must define `get_default_odm_query()`.

    Serializers that want to restrict which fields are used for filtering need to have a variable called
    filterable_fields which is a list of strings representing the field names as they appear in the serialization.
    """

    # TODO Handle simple and complex non-standard fields

    TRUTHY = set(['true', 'True', 1, '1'])
    FALSY = set(['false', 'False', 0, '0'])

    # For the field_comparison_operators, instances can be a class or a tuple of classes
    field_comparison_operators = [
        {
            'instances': ser.CharField,
            'comparison_operator': 'icontains'
        },
        {
            'instances': ser.ListField,
            'comparison_operator': 'in'
        }
    ]

    def get_comparison_operator(self, key, value):
        default_operator = 'eq'

        for operator in self.field_comparison_operators:
            if isinstance(self.serializer_class._declared_fields[key], operator['instances']):
                return operator['comparison_operator']

        return default_operator

    def is_filterable_field(self, key, value):
        try:
            return key.strip() in self.serializer_class.filterable_fields
        except AttributeError:
            return key.strip() in self.serializer_class._declared_fields

    def get_default_odm_query(self):
        raise NotImplementedError('Must define get_default_odm_query')

    def get_query_from_request(self):
        query = self.query_params_to_odm_query(self.request.QUERY_PARAMS)
        if not query:
            query = self.get_default_odm_query()
        return query

    def query_params_to_odm_query(self, query_params):
        """Convert query params to a modularodm Query object."""

        fields_dict = query_params_to_fields(query_params)
        if fields_dict:
            query_parts = [
                Q(self.convert_key(key, value), self.get_comparison_operator(key, value), self.convert_value(key, value))
                for key, value in fields_dict.items() if self.is_filterable_field(key, value)
            ]
            # TODO Ensure that if you try to filter on an invalid field, it returns a useful error.
            try:
                query = functools.reduce(intersect, query_parts)
            except TypeError:
                query = None
        else:
            query = None
        return query

    # Used so that that queries by _id will work
    def convert_key(self, key, value):
        key = key.strip()
        if self.serializer_class._declared_fields[key].source:
            return self.serializer_class._declared_fields[key].source
        return key

    # Used to convert string values from query params to Python booleans when necessary
    def convert_value(self, key, value):
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
