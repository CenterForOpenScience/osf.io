from rest_framework.exceptions import NotFound

#todo create node settings file?
standard_subquery_keys = {
    'count':0,
    'related':''
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
        query_keys = {}
        # Processes include string into ',' separated parameters with '.' marking relationships
        for raw_parameter in include.split(','):
            sub_query_list = raw_parameter.split('.')
            query = {}
            for subquery in reversed(sub_query_list):
                query = {subquery: query}
            query_keys[sub_query_list[0]] = query[sub_query_list[0]]
        query_params = query_keys
        for key in query_keys:
            if key not in allowed_query_keys:
                raise NotFound('Key {} is not a valid query parameter for node object.'.format(key))
            else:
                query_params[key] = self.process_key(key, query_params[key])
        self.query_params = query_params

    def process_key(self, key, default_value):
        return default_value