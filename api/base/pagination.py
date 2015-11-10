from collections import OrderedDict
from django.core.urlresolvers import reverse, resolve, _urlconfs, get_urlconf, set_urlconf, ResolverMatch, get_callable
from django.core.urlresolvers import get_resolver, RegexURLPattern, RegexURLResolver
from django.conf.urls import patterns, url

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
        embedded = self.request.parser_context['kwargs'].get('embedded')
        if 'embed' in self.request.query_params:
            if not embedded:
                url = replace_query_param(url, 'embed', self.request.query_params['embed'])

        url = replace_query_param(url, self.page_query_param, page_number)

        return url

    def get_first_real_link(self, url):
        if not self.page.has_previous():
            return None
        url = self.query_param_generator(self.request.build_absolute_uri(url))
        return remove_query_param(url, self.page_query_param)

    def get_last_real_link(self, url):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.paginator.num_pages
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_real_link(self, url):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    def get_next_real_link(self, url):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri(url)
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_paginated_response(self, data):
        kwargs = self.request.parser_context['kwargs'].copy()
        kwargs.pop('no_embeds', None)
        view_name = self.request.parser_context['view'].view_name

        response_dict = OrderedDict([
             ('data', data),
            ('links', OrderedDict([
                ('first', self.get_first_real_link(reverse(view_name, kwargs=kwargs))),
                ('last', self.get_last_real_link(reverse(view_name, kwargs=kwargs))),
                ('prev', self.get_previous_real_link(reverse(view_name, kwargs=kwargs))),
                ('next', self.get_next_real_link(reverse(view_name, kwargs=kwargs))),
                ('meta', OrderedDict([
                    ('total', self.page.paginator.count),
                    ('per_page', self.page.paginator.per_page),
                ]))
            ])),
        ])
        return Response(response_dict)
