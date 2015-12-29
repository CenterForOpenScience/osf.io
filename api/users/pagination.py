from collections import OrderedDict
from django.core.urlresolvers import reverse

from api.base.pagination import JSONAPIPagination
from rest_framework.response import Response

class UserNodeLogPagination(JSONAPIPagination):
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
        comments, nodes, wiki, files = self.get_count_of_action()
        if self.request.query_params.get('aggregate'):
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

    def get_count_of_action(self):
        logs_with_action = {}
        for log in self.page.paginator.object_list:
            if logs_with_action.get(log.action):
                logs_with_action[log.action].append(log)
            else:
                logs_with_action[log.action] = [log]

        return len(logs_with_action.get('comment_added') or []),\
               len(logs_with_action.get('project_created') or []) + len(logs_with_action.get('node_created') or []),\
               len(logs_with_action.get('wiki_updated') or []),\
               len(logs_with_action.get('osf_storage_file_updated') or []) + len(logs_with_action.get('osf_storage_file_added') or [])
