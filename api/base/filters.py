import re
import functools

from modularodm import Q
from rest_framework.filters import OrderingFilter


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
    """
    TRUTHY = set(['true', 'True', 1, '1'])
    FALSY = set(['false', 'False', 0, '0'])

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
                Q(self.convert_key(key, value), 'eq', self.convert_value(key, value)) for key, value in fields_dict.items()
            ]
            query = functools.reduce(intersect, query_parts)
        else:
            query = None
        return query

    # Used so that that queries by _id will work
    def convert_key(self, key, value):
        if key.strip() == 'id':
            return '_id'
        return key

    # Used to convert string values from query params to Python booleans when necessary
    def convert_value(self, key, val):
        val = val.strip()
        if val in self.TRUTHY:
            return True
        elif val in self.FALSY:
            return False
        # Convert me to current user's pk
        elif val == 'me' and not self.request.user.is_anonymous():
            return self.request.user.pk
        else:
            return val
