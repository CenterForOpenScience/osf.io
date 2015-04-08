from collections import OrderedDict

from rest_framework import pagination
from rest_framework.response import Response

class JSONAPIPagination(pagination.PageNumberPagination):
    """Custom paginator that formats responses in a JSON-API compatible format."""

    def get_paginated_response(self, data):
        response_dict = OrderedDict([
            ('data', data),
            ('links', OrderedDict([
                ('next', self.get_next_link()),
                ('previous', self.get_previous_link()),
                ('meta', OrderedDict([
                    ('count', self.page.paginator.count),
                ]))
            ])),
        ])
        return Response(response_dict)
