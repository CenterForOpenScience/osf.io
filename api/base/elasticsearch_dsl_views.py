from __future__ import annotations
import abc
import datetime
import typing

import elasticsearch_dsl as edsl
from rest_framework import generics, exceptions as drf_exceptions
from rest_framework.settings import api_settings as drf_settings
from api.base.settings.defaults import REPORT_FILENAME_FORMAT

if typing.TYPE_CHECKING:
    from rest_framework import serializers

from api.base.filters import FilterMixin
from api.base.views import JSONAPIBaseView
from api.metrics.renderers import (
    MetricsReportsCsvRenderer,
    MetricsReportsTsvRenderer,
    MetricsReportsJsonRenderer,
)
from api.base.pagination import ElasticsearchQuerySizeMaximumPagination, JSONAPIPagination
from api.base.renderers import JSONAPIRenderer


class ElasticsearchListView(FilterMixin, JSONAPIBaseView, generics.ListAPIView, abc.ABC):
    '''abstract view class using `elasticsearch_dsl.Search` as a queryset-analogue

    builds a `Search` based on `self.get_default_search()` and the request's
    query parameters for filtering, sorting, and pagination -- fetches only
    the data required for the response, just like with a queryset!
    '''
    serializer_class: type[serializers.BaseSerializer]  # required on subclasses

    default_ordering: str | None = None  # name of a serializer field, prepended with "-" for descending sort
    ordering_fields: frozenset[str] = frozenset()  # serializer field names

    @abc.abstractmethod
    def get_default_search(self) -> edsl.Search | None:
        '''the base `elasticsearch_dsl.Search` for this list, based on url path

        (common jsonapi query parameters will be considered automatically)
        '''
        ...

    FILE_RENDERER_CLASSES = {
        MetricsReportsCsvRenderer,
        MetricsReportsTsvRenderer,
        MetricsReportsJsonRenderer,
    }

    def set_content_disposition(self, response, renderer: str):
        """Set the Content-Disposition header to prompt a file download with the appropriate filename.

        Args:
            response: The HTTP response object to modify.
            renderer: The renderer instance used for the response, which determines the file extension.
        """
        current_date = datetime.datetime.now().strftime('%Y-%m')

        if isinstance(renderer, JSONAPIRenderer):
            extension = 'json'
        else:
            extension = getattr(renderer, 'extension', renderer.format)

        filename = REPORT_FILENAME_FORMAT.format(
            view_name=self.view_name,
            date_created=current_date,
            extension=extension,
        )

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

    def finalize_response(self, request, response, *args, **kwargs):
        # Call the parent method to finalize the response first
        response = super().finalize_response(request, response, *args, **kwargs)
        # Check if this is a direct download request or file renderer classes, set to the Content-Disposition header
        # so filename and attachment for browser download
        if isinstance(request.accepted_renderer, tuple(self.FILE_RENDERER_CLASSES)):
            self.set_content_disposition(response, request.accepted_renderer)

        return response

    ###
    # beware! inheritance shenanigans below

    # override FilterMixin to disable all operators besides 'eq' and 'ne'
    MATCHABLE_FIELDS = ()
    COMPARABLE_FIELDS = ()
    DEFAULT_OPERATOR_OVERRIDES = {}
    # (if you want to add fulltext-search or range-filter support, remove the override
    #  and update `__add_search_filter` to handle those operators -- tho note that the
    #  underlying elasticsearch field mapping will need to be compatible with the query)

    # override DEFAULT_FILTER_BACKENDS rest_framework setting
    # (filtering handled in-view to reuse logic from FilterMixin)
    filter_backends = ()

    # note: because elasticsearch_dsl.Search supports slicing and gives results when iterated on,
    #       it works fine with default pagination

    # override rest_framework.generics.GenericAPIView
    @property
    def pagination_class(self):
        """
        When downloading a file assume no pagination is necessary unless the user specifies
        """
        is_file_download = any(
            self.request.accepted_renderer.format == renderer.format
            for renderer in self.FILE_RENDERER_CLASSES
        )
        # if it's a file download of the JSON respect default page size
        if is_file_download:
            return ElasticsearchQuerySizeMaximumPagination
        return JSONAPIPagination

    def get_queryset(self):
        _search = self.get_default_search()
        if _search is None:
            return []
        # using parsing logic from FilterMixin (oddly nested dict and all)
        for _parsed_param in self.parse_query_params(self.request.query_params).values():
            for _parsed_filter in _parsed_param.values():
                _search = self.__add_search_filter(
                    _search,
                    elastic_field_name=_parsed_filter['source_field_name'],
                    operator=_parsed_filter['op'],
                    value=_parsed_filter['value'],
                )
        return self.__add_sort(_search)

    ###
    # private methods

    def __add_sort(self, search: edsl.Search) -> edsl.Search:
        _elastic_sort = self.__get_elastic_sort()
        return (search if _elastic_sort is None else search.sort(_elastic_sort))

    def __get_elastic_sort(self) -> str | None:
        _sort_param = self.request.query_params.get(drf_settings.ORDERING_PARAM, self.default_ordering)
        if not _sort_param:
            return None
        _sort_field, _ascending = (
            (_sort_param[1:], False)
            if _sort_param.startswith('-')
            else (_sort_param, True)
        )
        if _sort_field not in self.ordering_fields:
            raise drf_exceptions.ValidationError(
                f'invalid value for {drf_settings.ORDERING_PARAM} query param (valid values: {", ".join(self.ordering_fields)})',
            )
        _serializer_field = self.get_serializer().fields[_sort_field]
        _elastic_sort_field = _serializer_field.source
        return (_elastic_sort_field if _ascending else f'-{_elastic_sort_field}')

    def __add_search_filter(
        self,
        search: edsl.Search,
        elastic_field_name: str,
        operator: str,
        value: str,
    ) -> edsl.Search:
        match operator:  # operators from FilterMixin
            case 'eq':
                if value == '':
                    return search.exclude('exists', field=elastic_field_name)
                return search.filter('term', **{elastic_field_name: value})
            case 'ne':
                if value == '':
                    return search.filter('exists', field=elastic_field_name)
                return search.exclude('term', **{elastic_field_name: value})
            case _:
                raise NotImplementedError(f'unsupported filter operator "{operator}"')
