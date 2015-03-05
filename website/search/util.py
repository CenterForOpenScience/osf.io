import hashlib


def build_query(q='*', start=0, size=10, sort=None):
    query = {
        'query': build_query_string(q),
        'from': start,
        'size': size,
    }

    if sort:
        query['sort'] = [
            {
                sort: 'desc'
            }
        ]

    return query


def build_query_string(q):
    return {
        'query_string': {
            'default_field': '_all',
            'query': q,
            'analyze_wildcard': True,
            'lenient': True  # TODO, may not want to do this
        }
    }


def source_to_color(source):
    md5 = hashlib.md5()
    md5.update(source+'elephant')
    hash_value = md5.hexdigest()
    rgb = '#' + hash_value[0:2] + hash_value[2:4] + hash_value[4:6]
    return rgb
