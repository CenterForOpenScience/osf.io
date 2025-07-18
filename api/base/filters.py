import datetime
import functools
import operator
import re

import pytz
from api.base import utils
from api.base.exceptions import (
    InvalidFilterComparisonType,
    InvalidFilterError, InvalidFilterFieldError,
    InvalidFilterMatchType, InvalidFilterOperator,
    InvalidFilterValue,
)
from api.base.serializers import RelationshipField, ShowIfVersion, TargetField
from dateutil import parser as date_parser
from django.core.exceptions import ValidationError
from django.db.models import QuerySet as DjangoQuerySet
from django.db.models import Q
from rest_framework import serializers as ser
from rest_framework.filters import OrderingFilter
from osf.models import Subject, Preprint
from osf.models.base import GuidMixin, Guid
from functools import cmp_to_key
from framework import sentry

def lowercase(lower):
    if hasattr(lower, '__call__'):
        return lower()
    return lower


def sort_multiple(fields):
    fields = list(fields)

    def sort_fn(a, b):
        sort_direction = 1
        for field in fields:
            if field[0] == '-':
                sort_direction = -1
                field = field[1:]
            a_field = getattr(a, field)
            b_field = getattr(b, field)
            if a_field > b_field:
                return 1 * sort_direction
            elif a_field < b_field:
                return -1 * sort_direction
        return 0
    return sort_fn


class OSFOrderingFilter(OrderingFilter):
    """Adaptation of rest_framework.filters.OrderingFilter to work with modular-odm."""
    # override
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        if isinstance(queryset, DjangoQuerySet):
            if getattr(queryset.query, 'distinct_fields', None):
                order_fields = tuple([field.lstrip('-') for field in ordering])
                distinct_fields = queryset.query.distinct_fields
                queryset.query.distinct_fields = tuple(set(distinct_fields + order_fields))
            return super().filter_queryset(request, queryset, view)
        elif isinstance(ordering, (list, tuple)):
            sorted_list = sorted(queryset, key=cmp_to_key(sort_multiple(ordering)))
            return sorted_list
        else:
            raise NotImplementedError()

    def get_serializer_source_field(self, view, request):
        """
        Returns a dictionary of serializer fields and source names. i.e. {'date_created': 'created'}

        Logic borrowed from OrderingFilter.get_default_valid_fields with modifications to retrieve
        source fields for serializer field names.

        :param view api view
        :
        """
        field_to_source_mapping = {}

        if hasattr(view, 'get_serializer_class'):
            serializer_class = view.get_serializer_class()
        else:
            serializer_class = getattr(view, 'serializer_class', None)

        # This will not allow any serializer fields with nested related fields to be sorted on
        for field_name, field in serializer_class(context={'request': request}).fields.items():
            if not getattr(field, 'write_only', False) and not field.source == '*' and field_name != field.source:
                field_to_source_mapping[field_name] = field.source.replace('.', '_')

        return field_to_source_mapping

    # Overrides OrderingFilter
    def remove_invalid_fields(self, queryset, fields, view, request):
        """
        Returns an array of valid fields to be used for ordering.
        Any valid source fields which are input remain in the valid fields list using the super method.
        Serializer fields are mapped to their source fields and returned.
        :param fields, array, input sort fields
        :returns array of source fields for sorting.
        """
        valid_fields = super().remove_invalid_fields(queryset, fields, view, request)
        if not valid_fields:
            for invalid_field in fields:
                ordering_sign = '-' if invalid_field[0] == '-' else ''
                invalid_field = invalid_field.lstrip('-')

                field_source_mapping = self.get_serializer_source_field(view, request)
                source_field = field_source_mapping.get(invalid_field, None)
                if source_field:
                    valid_fields.append(ordering_sign + source_field)
        return valid_fields


class ElasticOSFOrderingFilter(OSFOrderingFilter):
    """ This is too enable sorting for ES endpoints that use ES results instead of a typical queryset"""
    def filter_queryset(self, request, queryset, view):
        sorted_list = queryset.copy()
        sort = request.query_params.get('sort')
        reverse = False
        if sort:
            if sort.startswith('-'):
                sort = sort.lstrip('-')
                reverse = True

            try:
                source = view.get_serializer_class()._declared_fields[sort].source
                sorted_list['results'] = sorted(queryset['results'], key=lambda item: item['_source'][source], reverse=reverse)
            except KeyError:
                pass

        return sorted_list


class FilterMixin:
    """ View mixin with helper functions for filtering. """

    QUERY_PATTERN = re.compile(r'^filter\[(?P<fields>((?:,*\s*\w+)*))\](\[(?P<op>\w+)\])?$')
    FILTER_FIELDS = re.compile(r'(?:,*\s*(\w+)+)')

    MATCH_OPERATORS = ('contains', 'icontains')
    MATCHABLE_FIELDS = (ser.CharField, ser.ListField)

    DEFAULT_OPERATORS = ('eq', 'ne')
    DEFAULT_OPERATOR_OVERRIDES = {
        ser.CharField: 'icontains',
        ser.ListField: 'contains',
    }

    NUMERIC_FIELDS = (ser.IntegerField, ser.DecimalField, ser.FloatField)

    DATE_FIELDS = (ser.DateTimeField, ser.DateField)
    DATETIME_PATTERN = re.compile(r'^\d{4}\-\d{2}\-\d{2}(?P<time>T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)$')

    COMPARISON_OPERATORS = ('gt', 'gte', 'lt', 'lte')
    COMPARABLE_FIELDS = NUMERIC_FIELDS + DATE_FIELDS

    LIST_FIELDS = (ser.ListField,)
    RELATIONSHIP_FIELDS = (RelationshipField, TargetField)

    MULTIPLE_VALUES_FIELDS = ['_id', 'guid._id', 'journal_id', 'moderation_state', 'event_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.serializer_class:
            raise NotImplementedError()

    def _get_default_operator(self, field):
        return self.DEFAULT_OPERATOR_OVERRIDES.get(type(field), 'eq')

    def _get_valid_operators(self, field):
        if isinstance(field, self.COMPARABLE_FIELDS):
            return self.COMPARISON_OPERATORS + self.DEFAULT_OPERATORS
        elif isinstance(field, self.MATCHABLE_FIELDS):
            return self.MATCH_OPERATORS + self.DEFAULT_OPERATORS
        else:
            return self.DEFAULT_OPERATORS

    def _get_field_or_error(self, field_name):
        """
        Check that the attempted filter field is valid

        :raises InvalidFilterError: If the filter field is not valid
        """
        serializer = self.get_serializer()
        if field_name not in serializer.fields:
            raise InvalidFilterError(detail=f"'{field_name}' is not a valid field for this endpoint.")
        if field_name not in getattr(serializer, 'filterable_fields', set()):
            raise InvalidFilterFieldError(parameter='filter', value=field_name)
        field = serializer.fields[field_name]
        # You cannot filter on deprecated fields.
        if isinstance(field, ShowIfVersion) and utils.is_deprecated(self.request.version, field.min_version, field.max_version):
            raise InvalidFilterFieldError(parameter='filter', value=field_name)
        return field

    def _validate_operator(self, field, field_name, op):
        """
        Check that the operator and field combination is valid

        :raises InvalidFilterComparisonType: If the query contains comparisons against non-date or non-numeric fields
        :raises InvalidFilterMatchType: If the query contains comparisons against non-string or non-list fields
        :raises InvalidFilterOperator: If the filter operator is not a member of self.COMPARISON_OPERATORS
        """
        if op not in set(self.MATCH_OPERATORS + self.COMPARISON_OPERATORS + self.DEFAULT_OPERATORS):
            valid_operators = self._get_valid_operators(field)
            raise InvalidFilterOperator(value=op, valid_operators=valid_operators)
        if op in self.COMPARISON_OPERATORS:
            if not isinstance(field, self.COMPARABLE_FIELDS):
                raise InvalidFilterComparisonType(
                    parameter='filter',
                    detail=f"Field '{field_name}' does not support comparison operators in a filter.",
                )
        if op in self.MATCH_OPERATORS:
            if not isinstance(field, self.MATCHABLE_FIELDS):
                raise InvalidFilterMatchType(
                    parameter='filter',
                    detail=f"Field '{field_name}' does not support match operators in a filter.",
                )

    def _parse_date_param(self, field, source_field_name, op, value):
        """
        Allow for ambiguous date filters. This supports operations like finding Nodes created on a given day
        even though Node.created is a specific datetime.

        :return list<dict>: list of one (specific datetime) or more (date range) parsed query params
        """
        time_match = self.DATETIME_PATTERN.match(value)
        if op != 'eq' or time_match:
            return {
                'op': op,
                'value': self.convert_value(value, field),
                'source_field_name': source_field_name,
            }
        else:  # TODO: let times be as generic as possible (i.e. whole month, whole year)
            start = self.convert_value(value, field)
            stop = start + datetime.timedelta(days=1)
            return [
                {
                    'op': 'gte',
                    'value': start,
                    'source_field_name': source_field_name,
                }, {
                    'op': 'lt',
                    'value': stop,
                    'source_field_name': source_field_name,
                },
            ]

    def bulk_get_values(self, value, field):
        """
        Returns list of values from query_param for IN query

        If url contained `/nodes/?filter[id]=12345, abcde`, the returned values would be:
        [u'12345', u'abcde']
        """
        value = value.lstrip('[').rstrip(']')
        separated_values = value.split(',')
        values = [self.convert_value(val.strip(), field) for val in separated_values]
        return values

    def parse_query_params(self, query_params):
        """Maps query params to a dict usable for filtering
        :param dict query_params:
        :return dict: of the format {
            <resolved_field_name>: {
                'op': <comparison_operator>,
                'value': <resolved_value>,
                'source_field_name': <model_field_source_of_serializer_field>
            }
        }
        """
        query = {}
        for key, value in query_params.items():
            match = self.QUERY_PATTERN.match(key)
            if match:
                match_dict = match.groupdict()
                fields = match_dict['fields']
                field_names = re.findall(self.FILTER_FIELDS, fields.strip())
                query.update({key: {}})

                for field_name in field_names:
                    field = self._get_field_or_error(field_name)
                    op = match_dict.get('op') or self._get_default_operator(field)
                    self._validate_operator(field, field_name, op)

                    source_field_name = field_name
                    if not isinstance(field, ser.SerializerMethodField):
                        source_field_name = self.convert_key(field)

                    # Special case date(time)s to allow for ambiguous date matches
                    if isinstance(field, self.DATE_FIELDS):
                        query.get(key).update({
                            field_name: self._parse_date_param(field, source_field_name, op, value),
                        })
                    elif not isinstance(value, int) and source_field_name in self.MULTIPLE_VALUES_FIELDS:
                        query.get(key).update({
                            field_name: {
                                'op': 'in',
                                'value': self.bulk_get_values(value, field),
                                'source_field_name': source_field_name,
                            },
                        })
                    elif not isinstance(value, int) and source_field_name == 'root':
                        query.get(key).update({
                            field_name: {
                                'op': op,
                                'value': self.bulk_get_values(value, field),
                                'source_field_name': source_field_name,
                            },
                        })
                    elif self.should_parse_special_query_params(field_name):
                        query = self.parse_special_query_params(field_name, key, value, query)
                    else:
                        query.get(key).update({
                            field_name: {
                                'op': op,
                                'value': self.convert_value(value, field),
                                'source_field_name': source_field_name,
                            },
                        })
                    self.postprocess_query_param(key, field_name, query[key][field_name])

        return query

    def postprocess_query_param(self, key, field_name, operation):
        """Hook to update parsed query parameters. Overrides of this method should either
        update ``operation`` in-place or do nothing.
        """
        pass

    def should_parse_special_query_params(self, field_name):
        """ This should be overridden in subclasses for custom filtering behavior
        """
        return False

    def parse_special_query_params(self, field_name, key, value, query):
        """ This should be overridden in subclasses for custom filtering behavior
        """
        pass

    def convert_key(self, field):
        """Used so queries on fields with the source or filter_key attributes set will work
        :param rest_framework.fields.Field field: Field instance
        """
        field = utils.decompose_field(field)
        filter_key = getattr(field, 'filter_key', None)
        if not filter_key:
            filter_key = (
                field.source
                if field.source not in (None, '*')
                else field.field_name
            )
        return filter_key

    def convert_value(self, value, field):
        """Used to convert incoming values from query params to the appropriate types for filter comparisons
        :param basestring value: value to be resolved
        :param rest_framework.fields.Field field: Field instance
        """
        field = utils.decompose_field(field)
        if isinstance(field, ser.BooleanField):
            if utils.is_truthy(value):
                return True
            elif utils.is_falsy(value):
                return False
            else:
                raise InvalidFilterValue(
                    value=value,
                    field_type='bool',
                )
        elif isinstance(field, self.DATE_FIELDS):
            try:
                ret = date_parser.parse(value, ignoretz=False)
                if not ret.tzinfo:
                    ret = ret.replace(tzinfo=pytz.utc)
                return ret
            except ValueError:
                raise InvalidFilterValue(
                    value=value,
                    field_type='date',
                )
        elif isinstance(field, (self.RELATIONSHIP_FIELDS, ser.SerializerMethodField, ser.ManyRelatedField)):
            if value == 'null':
                value = None
            return value
        elif isinstance(field, self.LIST_FIELDS) or isinstance((getattr(field, 'field', None)), self.LIST_FIELDS):
            if value == 'null':
                value = []
            return value
        else:
            try:
                return field.to_internal_value(value)
            except ValidationError:
                raise InvalidFilterValue(
                    value=value,
                )


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
        'gte': operator.ge,
    }

    def __init__(self, *args, **kwargs):
        super(FilterMixin, self).__init__(*args, **kwargs)
        if not self.serializer_class:
            raise NotImplementedError()

    def get_default_queryset(self):
        raise NotImplementedError('Must define get_default_queryset')

    def get_queryset_from_request(self):
        default_queryset = self.get_default_queryset()
        if not self.kwargs.get('is_embedded') and self.request.query_params:
            param_queryset = self.param_queryset(self.request.query_params, default_queryset)
            return param_queryset
        else:
            return default_queryset

    def param_queryset(self, query_params, default_queryset):
        """filters default queryset based on query parameters"""
        filters = self.parse_query_params(query_params)
        queryset = default_queryset
        query_parts = []

        if filters:
            for key, field_names in filters.items():

                sub_query_parts = []
                for field_name, data in field_names.items():
                    operations = data if isinstance(data, list) else [data]
                    if isinstance(queryset, list):
                        for operation in operations:
                            queryset = self.get_filtered_queryset(field_name, operation, queryset)
                    else:
                        sub_query_parts.append(
                            functools.reduce(
                                operator.and_, [
                                    self.build_query_from_field(field_name, operation)
                                    for operation in operations
                                ],
                            ),
                        )
                if not isinstance(queryset, list):
                    sub_query = functools.reduce(operator.or_, sub_query_parts)
                    query_parts.append(sub_query)

            if not isinstance(queryset, list):
                for query in query_parts:
                    queryset = queryset.filter(query)

        return queryset

    def build_query_from_field(self, field_name, operation):
        query_field_name = operation['source_field_name']
        if operation['op'] == 'ne':
            return ~Q(**{query_field_name: operation['value']})
        elif operation['op'] != 'eq':
            query_field_name = '{}__{}'.format(query_field_name, operation['op'])
            return Q(**{query_field_name: operation['value']})
        return Q(**{query_field_name: operation['value']})

    def postprocess_query_param(self, key, field_name, operation):
        # tag queries will usually be on Tag.name,
        # ?filter[tags]=foo should be translated to MQ('tags__name', 'eq', 'foo')
        # But queries on lists should be tags, e.g.
        # ?filter[tags]=foo,bar should be translated to MQ('tags', 'isnull', True)
        # ?filter[tags]=[] should be translated to MQ('tags', 'isnull', True)
        if field_name == 'tags':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = 'tags__name'
                operation['op'] = 'iexact'
            elif operation['value'] == []:
                operation['source_field_name'] = 'tags__isnull'
                operation['value'] = True
                operation['op'] = 'eq'
        # contributors iexact because guid matching
        if field_name == 'contributors':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = '_contributors__guids___id'
                operation['op'] = 'iexact'
        if field_name == 'kind':
            operation['source_field_name'] = 'is_file'
            # The value should be boolean
            operation['value'] = operation['value'] == 'file'
        if field_name == 'bibliographic':
            operation['op'] = 'exact'
        if field_name == 'permission':
            operation['op'] = 'exact'
        if field_name == 'id':
            operation['source_field_name'] = (
                'guids___id'
                if issubclass(self.model_class, GuidMixin)
                else self.model_class.primary_identifier_name
            )
            operation['op'] = 'in'
        if field_name == 'subjects':
            self.postprocess_subject_query_param(operation)

    def postprocess_subject_query_param(self, operation):
        if Subject.objects.filter(_id=operation['value']).exists():
            operation['source_field_name'] = 'subjects___id'
        else:
            operation['source_field_name'] = 'subjects__text'
            operation['op'] = 'iexact'

    def get_filtered_queryset(self, field_name, params, default_queryset):
        """filters default queryset based on the serializer field type"""
        field = self.serializer_class._declared_fields[field_name]
        source_field_name = params['source_field_name']

        if isinstance(field, ser.SerializerMethodField):
            return_val = [
                item for item in default_queryset
                if self.FILTERS[params['op']](self.get_serializer_method(field_name)(item), params['value'])
            ]
        elif isinstance(field, ser.CharField):
            if source_field_name in ('_id', 'root'):
                # Param parser treats certain ID fields as bulk queries: a list of options, instead of just one
                # Respect special-case behavior, and enforce exact match for these list fields.
                options = {item.lower() for item in params['value']}
                return_val = [
                    item for item in default_queryset
                    if getattr(item, source_field_name, '') in options
                ]
            else:
                return_val = [
                    item for item in default_queryset
                    if params['value'].lower() in getattr(item, source_field_name, '').lower()
                ]
        elif isinstance(field, ser.ListField):
            return_val = [
                item for item in default_queryset
                if params['value'].lower() in [
                    lowercase(i.lower) for i in getattr(item, source_field_name, [])
                ]
            ]
        else:
            try:
                return_val = [
                    item for item in default_queryset
                    if self.FILTERS[params['op']](getattr(item, source_field_name, None), params['value'])
                ]
            except TypeError:
                raise InvalidFilterValue(detail='Could not apply filter to specified field')

        return return_val

    def get_serializer_method(self, field_name):
        """
        :param field_name: The name of a SerializerMethodField
        :return: The function attached to the SerializerMethodField to get its value
        """
        serializer = self.get_serializer()
        serializer_method_name = 'get_' + field_name
        return getattr(serializer, serializer_method_name)


class PreprintFilterMixin(ListFilterMixin):
    """View mixin for many preprint listing views. It inherits from ListFilterMixin and customize postprocessing for
    preprint querying by provider, subjects and versioned `_id`.

    Note: Subclasses must define `get_default_queryset()`.
    """

    @staticmethod
    def postprocess_versioned_guid_id_query_param(operation):
        """Handle query parameters when filtering on `_id` for preprint which are now versioned.

        Note: preprint achieves versioning by using versioned guid, and thus no long has guid or guid._id for every
        version. Must convert `guid___id__in=` look-up to `pk__in` look-up.
        """
        preprint_pk_list = []
        for val in operation['value']:
            referent, version = Guid.load_referent(val)
            if referent is None:
                continue
            preprint_pk_list.append(referent.id)
        # Override the operation to filter `id__in=preprint_pk_list`
        operation['source_field_name'] = 'id__in'
        operation['value'] = preprint_pk_list
        operation['op'] = 'eq'

    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'provider':
            operation['source_field_name'] = 'provider___id'

        if field_name == 'id':
            PreprintFilterMixin.postprocess_versioned_guid_id_query_param(operation)

        if field_name == 'subjects':
            self.postprocess_subject_query_param(operation)

    def preprints_queryset(self, base_queryset, auth_user, allow_contribs=True, public_only=False, latest_only=False):
        preprints = Preprint.objects.can_view(
            base_queryset=base_queryset,
            user=auth_user,
            allow_contribs=allow_contribs,
            public_only=public_only,
        )
        if latest_only:
            preprints = preprints.filter(guids__isnull=False)
        return preprints


class TargetFilterMixin(ListFilterMixin):
    """View mixin for multi-content-type list views (e.g. `ReviewActionListCreate`). It inherits from `ListFilterMixin`
     and customizes the postprocessing of the `target` field when target is a preprint.

    Note: Subclasses must define `get_default_queryset()`.
    """

    @staticmethod
    def postprocess_preprint_as_target_query_param(operation, target_pk):
        """When target is a preprint, which must be versioned, the traditional non-versioned `guid___id==_id`
        look-up no longer works. Must convert it to PK look-up `target__id==pk`.
        """
        # Override the operation to filter `target__id==pk`
        operation['source_field_name'] = 'target__id'
        operation['value'] = target_pk
        operation['op'] = 'eq'

    def postprocess_query_param(self, key, field_name, operation):
        """Handles a special case when filtering on `target` when `target` is a Preprint.
        """
        if field_name == 'target':
            referent, version = Guid.load_referent(operation['value'])
            if referent:
                if version:
                    TargetFilterMixin.postprocess_preprint_as_target_query_param(operation, referent.id)
                else:
                    super().postprocess_query_param(key, field_name, operation)
            else:
                sentry.log_message(f'Target object invalid or not found: [target={operation['value']}]')
                return
        else:
            super().postprocess_query_param(key, field_name, operation)


class PreprintAsTargetFilterMixin(TargetFilterMixin):
    """View mixin for preprint related list views (e.g. `PreprintProviderWithdrawRequestList` and `PreprintActionList`).
    It inherits from `TargetFilterMixin` and customizes postprocessing the `target` field for preprint.

    Note: Subclasses must define `get_default_queryset()`.
    """

    def postprocess_query_param(self, key, field_name, operation):
        """Handles a special case when filtering on `target`.
        """
        if field_name == 'target':
            referent, version = Guid.load_referent(operation['value'])
            # A valid preprint must have referent and version
            if not referent or not version:
                sentry.log_message(f'Preprint invalid or note found: [target={operation['value']}]')
                return
            TargetFilterMixin.postprocess_preprint_as_target_query_param(operation, referent.id)
        else:
            super().postprocess_query_param(key, field_name, operation)
