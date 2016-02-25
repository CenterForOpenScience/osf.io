from collections import OrderedDict

from api.base.pagination import JSONAPIPagination


class UserLogPagination(JSONAPIPagination):

    node_log_aggregates = None

    def get_response_dict(self, data, url):
        response_dict = super(UserLogPagination, self).get_response_dict(data, url)
        if self.request.query_params.get('aggregates', False):
            comments, nodes, wiki, files = self.node_log_aggregates()
            meta = {
                'meta': OrderedDict([
                    ('aggregates', OrderedDict([
                        ('comments', comments),
                        ('wiki', wiki),
                        ('nodes', nodes),
                        ('files', files),
                    ])),
                    ('last_log_date', list(self.page.paginator.object_list)[-1].date if self.page.paginator.object_list else 0)
                ])
            }
            response_dict.update(meta)
        return response_dict
