from collections import OrderedDict
from django.core.urlresolvers import reverse, resolve, _urlconfs, get_urlconf, set_urlconf, ResolverMatch, get_callable
from django.core.urlresolvers import get_resolver, RegexURLPattern, RegexURLResolver
from django.conf.urls import patterns, url
from django.core.paginator import InvalidPage, Paginator as DjangoPaginator

from api.base.utils import absolute_reverse
from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.utils.urls import (
    replace_query_param, remove_query_param
)
from api.base.urls import patterns as base_patterns

class JSONAPIPagination(pagination.PageNumberPagination):
    """Custom paginator that formats responses in a JSON-API compatible format."""

    page_size_query_param = 'page[size]'

    def get_first_link(self):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        return remove_query_param(url, self.page_query_param)

    def get_last_link(self):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.paginator.num_pages
        return replace_query_param(url, self.page_query_param, page_number)

    def get_paginated_response(self, data):
        response_dict = OrderedDict([
            ('data', data),
            ('links', OrderedDict([
                ('first', self.get_first_link()),
                ('last', self.get_last_link()),
                ('prev', self.get_previous_link()),
                ('next', self.get_next_link()),
                ('meta', OrderedDict([
                    ('total', self.page.paginator.count),
                    ('per_page', self.page.paginator.per_page),
                ]))
            ])),
        ])
        return Response(response_dict)


class EmbeddedPagination(JSONAPIPagination):

    def query_param_generator(self, url, page_number):
        embedded = self.request.parser_context['kwargs'].get('no_embeds')
        if 'embed' in self.request.query_params:
            if not embedded:
                url = replace_query_param(url, 'embed', self.request.query_params['embed'])

        url = replace_query_param(url, self.page_query_param, page_number)

        if page_number == 1:
            return remove_query_param(url, self.page_query_param)

        return url

    def get_first_real_link(self, url):
        if not self.page.has_previous():
            return None
        return self.query_param_generator(self.request.build_absolute_uri(url), 1)

    def get_last_real_link(self, url):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.paginator.num_pages
        return self.query_param_generator(url, page_number)

    def get_previous_real_link(self, url):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.previous_page_number()
        return self.query_param_generator(url, page_number)

    def get_next_real_link(self, url):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.next_page_number()
        return self.query_param_generator(url, page_number)

    def get_paginated_response(self, data):
        kwargs = self.request.parser_context['kwargs'].copy()
        kwargs.pop('no_embeds', None)
        view_name = self.request.parser_context['view'].view_name
        reversed_url = reverse(view_name, kwargs=kwargs)

        response_dict = OrderedDict([
            ('data', data),
            ('links', OrderedDict([
                ('first', self.get_first_real_link(reversed_url)),
                ('last', self.get_last_real_link(reversed_url)),
                ('prev', self.get_previous_real_link(reversed_url)),
                ('next', self.get_next_real_link(reversed_url)),
                ('meta', OrderedDict([
                    ('total', self.page.paginator.count),
                    ('per_page', self.page.paginator.per_page),
                ]))
            ])),
        ])
        return Response(response_dict)

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        if request.parser_context['kwargs'].get('no_embeds'):
            page_size = self.get_page_size(request)

            paginator = DjangoPaginator(queryset, page_size)
            page_number = 1
            self.page = paginator.page(page_number)
            self.request = request
            return list(self.page)

        else:
            return super(EmbeddedPagination, self).paginate_queryset(queryset, request, view=None)
