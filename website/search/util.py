import random


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


def random_color(seed=15485863, max_iterations=15):
    def istooclose(color, colors, threshold=100):
        pairs = (color[0:2], color[2:4], color[4:6])
        for x in colors:
            distance = sum(abs(int(x[i], 16) - int(pairs[i], 16)) for i in xrange(3))
            if distance < threshold:
                return True
        return False

    random.seed(seed)
    values = [str(i) for i in range(10)] + ['A', 'B', 'C', 'D', 'E', 'F']
    colors = []
    iterations = 0
    while True:
        color = ''.join(random.choice(values) for i in range(6))
        if istooclose(color, colors) and not iterations > max_iterations:
            iterations += 1
            continue
        else:
            colors.append((color[0:2], color[2:4], color[4:6]))
            iterations = 0
        yield '#' + color
