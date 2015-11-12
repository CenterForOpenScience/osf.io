import re
import copy
import logging
import webcolors

from werkzeug.contrib.atom import AtomFeed

from website.util.sanitize import strip_html

logger = logging.getLogger(__name__)


COLORBREWER_COLORS = [(166, 206, 227), (31, 120, 180), (178, 223, 138), (51, 160, 44), (251, 154, 153), (227, 26, 28), (253, 191, 111), (255, 127, 0), (202, 178, 214), (106, 61, 154), (255, 255, 153), (177, 89, 40)]

RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                 u'|' + \
                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                 (unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                 unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                 unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff))

RE_XML_ILLEGAL_COMPILED = re.compile(RE_XML_ILLEGAL)


TITLE_WEIGHT = 4
DESCRIPTION_WEIGHT = 1.2
JOB_SCHOOL_BOOST = 1
ALL_JOB_SCHOOL_BOOST = 0.125

def build_query(qs='*', start=0, size=10, sort=None):
    query = {
        'query': build_query_string(qs),
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


# Match queryObject in search.js
def build_query_string(qs):
    field_boosts = {
        'title': TITLE_WEIGHT,
        'description': DESCRIPTION_WEIGHT,
        'job': JOB_SCHOOL_BOOST,
        'school': JOB_SCHOOL_BOOST,
        'all_jobs': ALL_JOB_SCHOOL_BOOST,
        'all_schools': ALL_JOB_SCHOOL_BOOST,
        '_all': 1,

    }

    fields = ['{}^{}'.format(k, v) for k, v in field_boosts.iteritems()]
    return {
        'query_string': {
            'default_field': '_all',
            'fields': fields,
            'query': qs,
            'analyze_wildcard': True,
            'lenient': True  # TODO, may not want to do this
        }
    }


def compute_start(page, size):
    try:
        start = (int(page) - 1) * size
    except ValueError:
        start = 0

    if start < 0:
        start = 0

    return start


def generate_color():
    # TODO - this might not be the optimal way - copy is expensive
    colors_to_generate = copy.copy(COLORBREWER_COLORS)
    colors_used = []

    while True:
        try:
            color = colors_to_generate.pop(0)
            colors_used.append(color)
        except IndexError:
            new_colors = get_new_colors(colors_used)
            colors_to_generate = new_colors
            colors_used = []
        yield [webcolors.rgb_to_hex(color), color]


def calculate_distance_between_colors(color1, color2):
    """ Takes 2 color tupes and returns the average between them
    """
    return ((color1[0] + color2[0]) / 2, (color1[1] + color2[1]) / 2, (color1[2] + color2[2]) / 2)


def get_new_colors(colors_used):
    new_colors = []
    for i in xrange(len(colors_used) - 1):
        new_colors.append(calculate_distance_between_colors(colors_used[i], colors_used[i + 1]))

    return new_colors


def create_atom_feed(name, data, query, size, start, url, to_atom):
    if query == '*':
        title_query = 'All'
    else:
        title_query = query

    title = '{name}: Atom Feed for query: "{title_query}"'.format(name=name, title_query=title_query)
    author = 'COS'

    links = [
        {'href': '{url}?page=1'.format(url=url), 'rel': 'first'},
        {'href': '{url}?page={page}'.format(url=url, page=(start / size) + 2), 'rel': 'next'},
        {'href': '{url}?page={page}'.format(url=url, page=(start / size)), 'rel': 'previous'}
    ]

    links = links[1:-1] if (start / size) == 0 else links

    feed = AtomFeed(
        title=title,
        feed_url=url,
        author=author,
        links=links
    )

    for doc in data:
        try:
            feed.add(**to_atom(doc))
        except ValueError as e:
            logger.error('Atom feed error for source {}'.format(doc.get('source')))
            logger.exception(e)

    return feed


def html_and_illegal_unicode_replace(atom_element):
    """ Replace an illegal for XML unicode character with nothing.
    This fix thanks to Matt Harper from his blog post:
    https://maxharp3r.wordpress.com/2008/05/15/pythons-minidom-xml-and-illegal-unicode-characters/
    """
    if atom_element:
        new_element = RE_XML_ILLEGAL_COMPILED.sub('', atom_element)
        return strip_html(new_element)
    return atom_element
