from collections import OrderedDict

from api.base.pagination import JSONAPIPagination


class UserNodeLogPagination(JSONAPIPagination):

    node_log_aggregates = None

    def get_response_dict(self, data, url):
        if self.request.query_params.get('aggregates'):
            comments, nodes, wiki, files = self.node_log_aggregates()
            response_dict = OrderedDict([
                ('data', data),
                ('links', OrderedDict([
                    ('first', self.get_first_real_link(url)),
                    ('last', self.get_last_real_link(url)),
                    ('prev', self.get_previous_real_link(url)),
                    ('next', self.get_next_real_link(url)),
                    ('meta', OrderedDict([
                        ('total', self.page.paginator.count),
                        ('per_page', self.page.paginator.per_page),
                    ]))
                ])),
                ('meta', OrderedDict([
                    ('aggregates', OrderedDict([
                        ('comments', comments),
                        ('wiki', wiki),
                        ('nodes', nodes),
                        ('files', files),
                    ])),
                    ('last_log_date', list(self.page.paginator.object_list)[-1].date if self.page.paginator.object_list else 0)
                ]))
            ])
        else:
            response_dict = OrderedDict([
                ('data', data),
                ('links', OrderedDict([
                    ('first', self.get_first_real_link(url)),
                    ('last', self.get_last_real_link(url)),
                    ('prev', self.get_previous_real_link(url)),
                    ('next', self.get_next_real_link(url)),
                    ('meta', OrderedDict([
                        ('total', self.page.paginator.count),
                        ('per_page', self.page.paginator.per_page)
                    ]))
                ])),
            ])
        return response_dict
