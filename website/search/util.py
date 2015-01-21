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

def format_mapping(running, parents=(), seperator='.', flatten=False):
    ret = {}
    for key, value in running.items():
        if flatten:
            path = seperator.join(parents + (key, ))
        else:
            path = key

        if value.get('type'):
            ret[path] = value['type']
        else:
            sub_ret = format_mapping(value['properties'], parents + (key, ), seperator=seperator, flatten=flatten)

            if flatten:
                ret[path] = 'object'
                ret.update(sub_ret)
            else:
                ret[path] = sub_ret
    return ret
