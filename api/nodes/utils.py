from rest_framework.exceptions import NotFound

#todo create node settings file?
standard_subquery_keys = {
    'count': 0,
    'related': ''
}

allowed_query_keys = {
    'contributors': standard_subquery_keys,
    'children': standard_subquery_keys,
    'pointers': standard_subquery_keys,
    'registrations': standard_subquery_keys
}

class IncludeParamsProcessor(object):
    #todo move into base/utils?
    def __init__(self, include):

        # Checks and cuts off include value if '/' is found
        include = include.split('/')[0]
        query_params = {}

        # Processes include string into ',' separated parameters with '.' marking relationships
        for raw_parameter in include.split(','):
            sub_query_list = raw_parameter.split('.')
            query = {}
            allowed_keys = allowed_query_keys
            for sub_query in reversed(sub_query_list):
                query = {sub_query: query}
            for sub_query_test in sub_query_list:
                if sub_query_test in allowed_keys:
                    allowed_keys = allowed_keys[sub_query_test]
                else:
                    raise NotFound('{} is not a valid property of the Node object.'.format(query))
            query = self.process_query(query)
            query_params[sub_query_list[0]] = query[sub_query_list[0]]
        self.additional_query_params = query_params

    def process_query(self, query, allowed_keys=None):
        return query
