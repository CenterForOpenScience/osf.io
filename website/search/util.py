def build_query(q='*', start=0, size=10):
    return {
        'query': build_query_string(q),
        'from': start,
        'size': size,
    }


def build_query_string(q):
    return {
        'query_string': {
            'default_field': '_all',
            'query': q,
            'analyze_wildcard': True,
            'lenient': True  # TODO, may not want to do this
        }
    }
