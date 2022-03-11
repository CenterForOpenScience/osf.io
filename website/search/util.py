# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import re
import unicodedata

from website import settings

logger = logging.getLogger(__name__)

if settings.SEARCH_ANALYZER == settings.SEARCH_ANALYZER_JAPANESE:
    DEFAULT_OPERATOR = 'AND'
else:
    DEFAULT_OPERATOR = 'OR'

TITLE_WEIGHT = 4
DESCRIPTION_WEIGHT = 1.2
JOB_SCHOOL_BOOST = 1
ALL_JOB_SCHOOL_BOOST = 0.125


def validate_email(user_email):
    if user_email is not None:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return bool(re.fullmatch(regex, user_email))

    return False


def build_query(qs='*', start=0, size=10, sort=None, match_value=None, match_key=None):
    query_body = build_query_string(qs)
    if isinstance(match_key, str) and match_value is not None:
        if match_key == 'emails':
            build_query_emails = 'emails:' + match_value
            query_body = {
                'bool': {
                    'should': [
                        {
                            'query_string': {
                                'default_operator': 'AND',
                                'query': build_query_emails
                            }
                        }
                    ]
                }
            }
        else:
            query_body = {
                'bool': {
                    'should': [
                        query_body,
                        {
                            'match': {
                                match_key: {
                                    'query': match_value,
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

    # for highlight
    add_fields = ['name', 'user', 'text', 'comments.*']
    for f in add_fields:
        fields.append('{}^1'.format(f))
        fields.append('{}.*^1'.format(f))

    return {
        'query_string': {
            'default_operator': DEFAULT_OPERATOR,
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
    return unicode_normalize(new_text)


def es_escape(text):
    # see https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#_reserved_characte
    text = re.sub(r'(?P<ES>[+\-=&|!(){}\[\]^"~*?:\\/])', r'\\\g<ES>', text)

    # NOTE: < and > cannot be escaped at all. The only way to prevent
    # them from attempting to create a range query is to remove them
    # from the query string entirely.
    return re.sub(r'(?P<ES>[><])', ' ', text)


def _is_delimiter(char):
    # FIXME: re.UNICODE is unnecessary in Python3
    return re.match(r'\s\Z', char) or char in [u'(', u')']


def quote(string):
    """
    return: (quoted_string, quoted)
    """

    # Alphanumeric with * or ? string is not quoted.
    # e.g. abc* -> abc*
    # If abc* is quoted, ...
    #   bad pattern 1: "abc"* -> equivalent "abc" OR * -> matche all
    #   bat pattern 2: "abc*" -> equivalent "abc " -> match "abc" only

    # FIXME: flags=re.ASCII is necessary in Python3
    if re.match(r'[\w\*\?]+\Z', string, flags=re.ASCII):
        return (string, False)
    else:
        return (u'"{}"'.format(string), True)  # quoted


def _quote(string):
    s, _ = quote(string)
    return s


def _quote_token(token):
    """
    quoting Elasticsearch query string:
    https://www.elastic.co/guide/en/elasticsearch/reference/2.3/query-dsl-query-string-query.html#query-string-syntax
    """

    if token in [u'AND', u'OR', u'NOT', u'&&', u'||', u'!']:
        return token

    m = re.match(
        r'(?P<prefix_op>\+|-)?' +
        r'(?P<body>(?:\\.|[^\\~\^])+)?' +
        r'(?P<suffix_op>(?:~|\^)[0-9\.]*)?\Z',
        token
    )

    if m is None:
        return token

    prefix_op = m.group('prefix_op')
    suffix_op = m.group('suffix_op')
    body = m.group('body')
    res = u''

    if prefix_op is not None:
        res += prefix_op

    if body is not None:
        parts = [u'']

        in_escape = False
        for c in body:
            # backslash escape
            if in_escape:
                parts[-1] += c
                in_escape = False
            elif c == u'\\':
                parts[-1] += c
                in_escape = True
            elif c == u':':
                parts.append(c)
                parts.append(u'')
            else:
                parts[-1] += c

        if u':' not in parts:
            res += _quote(body)
        else:
            has_key = False
            for part in parts:
                if not part:
                    continue
                is_colon = part == u':'
                if is_colon or not has_key:
                    res += part
                    if is_colon:
                        has_key = True
                else:
                    res += _quote(part)

    if suffix_op is not None:
        res += suffix_op

    return res


def quote_query_string(chars):
    """
    Multibyte charactor string is quoted by double quote.
    Because english analyzer of Elasticsearch decomposes
    multibyte character strings with OR expression.
    e.g. 神保町 -> 神 OR 保 OR 町
         "神保町"-> 神保町
    """

    if not isinstance(chars, str):
        chars = chars.decode('utf-8')

    token = u''
    qs = u''
    in_escape = False
    in_quote = False
    in_token = False

    for c in chars:
        # backslash escape
        if in_escape:
            token += c
            in_escape = False
            continue
        if c == u'\\':
            token += c
            in_escape = True
            continue

        # quote
        if c != u'"' and in_quote:
            token += c
            continue
        if c == u'"' and in_quote:
            token += c
            qs += token
            token = u''
            in_quote = False
            continue

        # otherwise: not in_quote

        if _is_delimiter(c) or c == u'"':
            if in_token:
                qs += _quote_token(token)
                token = u''
                in_token = False
            if c == u'"':
                token += c
                in_quote = True
            else:
                qs += c
            continue

        # otherwise: not _is_delimiter(c)
        token += c
        in_token = True

    if token:
        qs += _quote_token(token)

    return qs

NORMALIZED_FIELDS = ('user', 'names', 'title', 'description', 'name', 'tags')

def replace_normalized_field(qs):
    for name in NORMALIZED_FIELDS:
        qs = re.sub('(^|[\\(\\s]){}\\:'.format(name),
                    '\\1normalized_{}:'.format(name), qs)
    return qs

def convert_query_string(qs, normalize=False):
    if settings.SEARCH_ANALYZER == settings.SEARCH_ANALYZER_ENGLISH:
        qs = quote_query_string(qs)
        qs = replace_normalized_field(qs)
    logger.debug(u'convert_query_string: {}'.format(qs))
    if normalize:
        return unicode_normalize(qs)
    else:
        return qs

def build_private_search_query(user, qs='*', start=0, size=10, sort=None, highlight=None):
    match_node = {
        'bool': {
            'must': [
                {
                    'terms': {
                        'category': [
                            'project',
                            'component',
                            'registration',
                            'preprint'
                        ]
                    }
                },
                {
                    'bool': {
                        'should': [
                            {
                                'term': {
                                    'node_contributors.id': user._id
                                }
                            },
                            {
                                'term': {
                                    'public': True
                                }
                            }
                        ]
                    }
                }
            ]
        }
    },

    match_file = {
        'bool': {
            'must': [
                {
                    'term': {
                        'category': 'file'
                    }
                },
                {
                    'bool': {
                        'should': [
                            {
                                'term': {
                                    'node_contributors.id': user._id
                                }
                            },
                            {
                                'term': {
                                    'node_public': True
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    match_wiki = {
        'bool': {
            'must': [
                {
                    'term': {
                        'category': 'wiki'
                    }
                },
                {
                    'bool': {
                        'should': [
                            {
                                'term': {
                                    'node_contributors.id': user._id
                                }
                            },
                            {
                                'term': {
                                    'node_public': True
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    match_comment = {
        'bool': {
            'must': [
                {
                    'term': {
                        'category': 'comment'
                    }
                },
                {
                    'bool': {
                        'should': [
                            {
                                'term': {
                                    'node_contributors.id': user._id
                                }
                            },
                            {
                                'term': {
                                    'node_public': True
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    inner_query = build_query_string(qs)

    query_body = {
        'bool': {
            # This is a filter to search only accessible data.
            # If bool query context is used in a "filter"
            # context and it has "should" clauses then at least
            # one "should" clause is required to match.
            # So "must" is used instead of "filter" here.
            # See: https://www.elastic.co/guide/en/elasticsearch/reference/2.3/query-dsl-bool-query.html
            'must': [
                inner_query,
                {
                    'bool': {
                        'should': [
                            match_node,
                            match_file,
                            match_wiki,
                            match_comment,
                            {
                                'terms': {
                                    'category': [
                                        'user',
                                        'institution',
                                        'collectionsubmission'
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    highlight_fields = {}
    # Example:
    # highlight='title:30,comments.*:30'
    #   ->
    # highlight_fields = {
    #     'title': {
    #         'fragment_size': 30,
    #     },
    #     'comments.*': {
    #         'fragment_size': 124,
    #     },
    # }
    if highlight:
        fields = highlight.split(',')
        for field in fields:
            key_val = field.split(':')
            if len(key_val) >= 1:
                key = key_val[0]
                if len(key_val) == 2:
                    try:
                        val = int(key_val[1])
                    except Exception:
                        val = settings.SEARCH_HIGHLIGHT_FRAGMENT_SIZE
                else:
                    val = settings.SEARCH_HIGHLIGHT_FRAGMENT_SIZE
                highlight_fields[key] = {'fragment_size': val}
                highlight_fields[key + '.*'] = {'fragment_size': val}

    query = {
        'query': query_body,
        'highlight': {
            'number_of_fragments': 1,
            'pre_tags': ['<b>'],
            'post_tags': ['</b>'],
            'fields': highlight_fields,
            'require_field_match': False,
            'highlight_query': inner_query,
        },
        'from': start,
        'size': size,
        'sort': sort_query(sort),
    }
    return query

def sort_query(sort):
    if sort is None:  # default
        sort = 'modified_desc'

    def _split_target_order(sort):
        try:
            to = sort.split('_')
            return to[0], to[1]
        except Exception:
            return None, None

    target, order = _split_target_order(sort)

    ASC = 'asc'
    DESC = 'desc'
    MODIFIED = 'date_modified'
    CREATED = 'date_created'
    PROJECT = 'sort_node_name'
    FILE = 'sort_file_name'
    WIKI = 'sort_wiki_name'
    USER = 'sort_user_name'
    INSTITUTION = 'sort_institution_name'
    SCORE = '_score'

    ERROR = 'unknown sort parameter: {}'.format(sort)

    if order != ASC and order != DESC:
        # order = None  # use default
        raise Exception(ERROR)

    if target == 'project':
        query = [
            {PROJECT: order},
            {FILE: order},
            {WIKI: order},
            {USER: order},
            {INSTITUTION: order},
            {MODIFIED: DESC},
            {SCORE: ASC}
        ]
    elif target == 'file':
        query = [
            {FILE: order},
            {PROJECT: order},
            {WIKI: order},
            {USER: order},
            {INSTITUTION: order},
            {MODIFIED: DESC},
            {SCORE: ASC}
        ]
    elif target == 'wiki':
        query = [
            {WIKI: order},
            {PROJECT: order},
            {FILE: order},
            {USER: order},
            {INSTITUTION: order},
            {MODIFIED: DESC},
            {SCORE: ASC}
        ]
    elif target == 'user':
        query = [
            {USER: order},
            {PROJECT: order},
            {WIKI: order},
            {FILE: order},
            {INSTITUTION: order},
            {MODIFIED: DESC},
            {SCORE: ASC}
        ]
    elif target == 'institution':
        query = [
            {INSTITUTION: order},
            {PROJECT: order},
            {WIKI: order},
            {FILE: order},
            {USER: order},
            {MODIFIED: DESC},
            {SCORE: ASC}
        ]
    elif target == 'created':
        query = [
            {CREATED: order},
            {PROJECT: ASC},
            {FILE: ASC},
            {WIKI: ASC},
            {USER: ASC},
            {INSTITUTION: ASC},
            {SCORE: ASC}
        ]
    elif target == 'modified':
        query = [
            {MODIFIED: order},
            {PROJECT: ASC},
            {FILE: ASC},
            {WIKI: ASC},
            {USER: ASC},
            {INSTITUTION: ASC},
            {SCORE: ASC}
        ]
    else:
        raise Exception(ERROR)

    return query

def unicode_normalize(text):
    if text is None:
        return None
    if settings.SEARCH_ANALYZER == settings.SEARCH_ANALYZER_JAPANESE:
        return text
    if not isinstance(text, str):
        text = text.decode('utf-8')
    normalized = unicodedata.normalize('NFKD', text)
    if not settings.ENABLE_MULTILINGUAL_SEARCH:
        normalized = normalized.encode('ascii', 'ignore').decode('utf-8')
    return normalized
