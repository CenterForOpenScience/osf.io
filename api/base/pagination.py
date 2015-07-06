from collections import OrderedDict

from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.utils.urls import (
    replace_query_param, remove_query_param
)

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
