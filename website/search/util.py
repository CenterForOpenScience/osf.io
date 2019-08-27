import logging
import re

logger = logging.getLogger(__name__)


TITLE_WEIGHT = 4
DESCRIPTION_WEIGHT = 1.2
JOB_SCHOOL_BOOST = 1
ALL_JOB_SCHOOL_BOOST = 0.125

def build_query(qs='*', start=0, size=10, sort=None, user_guid=None):
    query_body = build_query_string(qs)
    if user_guid is not None:
        query_body = {
            'bool': {
                'should': [
                    query_body,
                    {
                        'match': {
                            'id': {
                                'query': user_guid,
                                'boost': 10.0
                            }
                        }
                    }
                ]
            }
        }
    query = {
        'query': query_body,
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

    fields = ['{}^{}'.format(k, v) for k, v in field_boosts.items()]
    return {
        'query_string': {
            'default_field': '_all',
            'fields': fields,
            'query': qs,
            'analyze_wildcard': True,
            'lenient': True  # TODO, may not want to do this
        }
    }

def clean_splitters(text):
    new_text = text.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    if new_text == text:
        return ''
    return new_text


def es_escape(text):
    # see https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_reserved_characte
    text = re.sub(r'(?P<ES>[+\-=&|!(){}\[\]^"~*?:\\/])', r'\\\g<ES>', text)

    # NOTE: < and > cannot be escaped at all. The only way to prevent
    # them from attempting to create a range query is to remove them
    # from the query string entirely.
    return re.sub(r'(?P<ES>[><])', ' ', text)
