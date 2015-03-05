import random
import webcolors
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


def color_too_close(color, colors, threshold=100):
    """
    For the random_color function, calculates the distance between
    two colors and returns False if they are closer than the threshold
    """
    for x in colors:
        distance = sum(abs(x[i] - color[i]) for i in xrange(3))
        if distance < threshold:
            return True
    return False


def random_color(seed=4545, max_iterations=15, threshold=100):
    """
    A Generator for random hex colors.
    Generates a sequence of colors that are different up to some threshold
    """
    random.seed(seed)
    colors = []
    iterations = 0
    while True:
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        if color_too_close(color, colors, threshold) and not iterations > max_iterations:
            iterations += 1
            continue
        else:
            colors.append(color)
            iterations = 0
        yield webcolors.rgb_to_hex(color)


def source_to_color(source):
    md5 = hashlib.md5()
    md5.update(source+'yo')
    hash_value = md5.hexdigest()
    rgb = '#' + hash_value[0:2] + hash_value[2:4] + hash_value[4:6]
    return rgb
