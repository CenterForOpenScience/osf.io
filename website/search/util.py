# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import re
import unicodedata

from website import settings

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


def _is_delimiter(char):
    # XXX FIXME: Python3に移行するときはre.UNICODEフラグを取り除くべき
    return re.match(r'\s\Z', char, flags=re.UNICODE) or char in [u'(', u')']


def quote(string):
    """
    return: (quoted_string, quoted)
    """

    # ダブルクオートで囲まれた文字列の中や後にワイルドカード(*と?)を付
    # 与すると意図した動作をしないため、ASCIIの英数字及びワイルドカー
    # ドのみで構成されるトークンの場合はダブルクオートで囲まない。
    # e.g. abc*
    # 期待: abc及びその後に文字が任意数続く検索対象にヒット
    # クオート1: "abc"* は "abc" OR * 相当。全ての検索対象にヒット
    # クオート2: "abc*" は "abc " 相当。abcとある検索対象のみにヒット
    # XXX FIXME: Python3に移行するときはflags=re.ASCIIを追加する
    if re.match(r'[\w\*\?]+\Z', string):
        return (string, False)
    else:
        return (u'"{}"'.format(string), True)


def _quote(string):
    s, _ = quote(string)
    return s


def _quote_token(token):
    """
    Elasticsearch query string言語のクオーティング
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
    Elasticsearchのenglish analyzerで漢字の単語を検索すると一文字ずつ
    トークンとして分解されてOR検索されてしまうため、ダブルクオートで囲
    んで(クオーティング)ひとまとまりとして扱うようにする。
    e.g. 「神保町」は「神」か「保」か「町」を検索する。
    一方、「"神保町"」は「神保町」を検索する。
    """

    if not isinstance(chars, unicode):
        raise TypeError('quote_query_string argument must be str type or unicode type.')

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


def build_private_search_query(user, qs='*', start=0, size=10, sort=None):
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
                                    'contributors.id': user._id
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

    query_body = {
        'bool': {
            'must': [
                build_query_string(qs),
                # 自分に関係ない他人のプライベートなデータを見ないよう
                # にするための絞り込み。
                # 下記のクエリは検索対象の除外が目的なのでmustではなく
                # filterを使うべきだが、filter contextの中でboolクエリ
                # のshould句を使う場合は必ずひとつ以上はヒットしなけれ
                # ばならない制限があるため、mustで絞り込んでいる。
                # https://www.elastic.co/guide/en/elasticsearch/reference/2.3/query-dsl-bool-query.html
                {
                    'bool': {
                        'should': [
                            match_node,
                            match_file,
                            {
                                'terms': {
                                    'category': [
                                        'user',
                                        'institution',
                                        'collectionSubmission'
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }

    return {
        'query': query_body,
        'from': start,
        'size': size,
    }

def normalize(text):
    normalized = unicodedata.normalize('NFKD', text)
    if not settings.ENABLE_MULTILINGUAL_SEARCH:
        normalized = normalized.encode('ascii', 'ignore')
    return normalized
