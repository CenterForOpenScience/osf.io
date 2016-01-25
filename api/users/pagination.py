from collections import OrderedDict
from django.core.urlresolvers import reverse

from api.base.pagination import JSONAPIPagination
from rest_framework.response import Response

class UserNodeLogPagination(JSONAPIPagination):

    node_log_aggregates = None

    def get_paginated_response(self, data):
        """
        Formats paginated response in accordance with JSON API.

        Creates pagination links from the view_name if embedded resource,
        rather than the location used in the request.
        """
        kwargs = self.request.parser_context['kwargs'].copy()
        embedded = kwargs.pop('is_embedded', None)
        view_name = self.request.parser_context['view'].view_fqn
        reversed_url = None
        if embedded:
            reversed_url = reverse(view_name, kwargs=kwargs)
        if self.request.query_params.get('aggregate'):
            comments, nodes, wiki, files = self.node_log_aggregates()
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
                        ('aggregates', OrderedDict([
                            ('comments', comments),
                            ('wiki', wiki),
                            ('nodes', nodes),
                            ('files', files),
                        ])),
                        ('last_log_date', list(self.page.paginator.object_list)[-1].date if self.page.paginator.object_list else 0)
                    ]))
                ])),
            ])
        else:
            response_dict = OrderedDict([
                ('data', data),
                ('links', OrderedDict([
                    ('first', self.get_first_real_link(reversed_url)),
                    ('last', self.get_last_real_link(reversed_url)),
                    ('prev', self.get_previous_real_link(reversed_url)),
                    ('next', self.get_next_real_link(reversed_url)),
                    ('meta', OrderedDict([
                        ('total', self.page.paginator.count),
                        ('per_page', self.page.paginator.per_page)
                    ]))
                ])),
            ])
        return Response(response_dict)
