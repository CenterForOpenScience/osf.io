from __future__ import unicode_literals

from time import gmtime
from calendar import timegm
from datetime import datetime

import pytz

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from elasticsearch import Elasticsearch

from website import settings
from website.search.elastic_search import requires_search

from util import generate_color, html_and_illegal_unicode_replace

import logging

logger = logging.getLogger(__name__)

share_es = Elasticsearch(
    settings.SHARE_ELASTIC_URI,
    request_timeout=settings.ELASTIC_TIMEOUT
)

# This is temporary until we update the backend
FRONTEND_VERSION = 1


@requires_search
def search(query, raw=False, index='share'):
    # Run the real query and get the results
    results = share_es.search(index=index, doc_type=None, body=query)

    for hit in results['hits']['hits']:
        hit['_source']['highlight'] = hit.get('highlight', {})
        if hit['_source'].get('shareProperties'):
            hit['_source']['shareProperties']['docID'] = hit['_source']['shareProperties'].get('docID') or hit['_id']
            hit['_source']['shareProperties']['source'] = hit['_source']['shareProperties'].get('source') or hit['_type']
    return results if raw else {
        'results': [hit['_source'] for hit in results['hits']['hits']],
        'count': results['hits']['total'],
        'aggregations': results.get('aggregations'),
        'aggs': results.get('aggs')
    }

def remove_key(d, k):
    d.pop(k, None)
    return d


def clean_count_query(query):
    # Get rid of fields not allowed in count queries
    for field in ['from', 'size', 'aggs', 'aggregations']:
        if query.get(field) is not None:
            del query[field]
    return query


@requires_search
def count(query, index='share'):
    query = clean_count_query(query)

    if settings.USE_SHARE:
        count = share_es.count(index=index, body=query)['count']
    else:
        count = 0

    return {
        'results': [],
        'count': count
    }


@requires_search
def providers():

    provider_map = share_es.search(index='share_providers', doc_type=None, body={
        'query': {
            'match_all': {}
        },
        'size': 10000
    })

    return {
        'providerMap': {
            hit['_source']['short_name']: hit['_source'] for hit in provider_map['hits']['hits']
        }
    }


@requires_search
def stats(query=None):
    query = query or {"query": {"match_all": {}}}

    index = settings.SHARE_ELASTIC_INDEX_TEMPLATE.format(FRONTEND_VERSION)

    three_months_ago = timegm((datetime.now() + relativedelta(months=-3)).timetuple()) * 1000
    query['aggs'] = {
        "sources": {
            "terms": {
                "field": "_type",
                "size": 0,
                "min_doc_count": 0,
            }
        },
        "doisMissing": {
            "filter": {
                "missing": {
                    "field": "id.doi"
                }
            },
            "aggs": {
                "sources": {
                    "terms": {
                        "field": "_type",
                        "size": 0
                    }
                }
            }
        },
        "dois": {
            "filter": {
                "exists": {
                    "field": "id.doi"
                }
            },
            "aggs": {
                "sources": {
                    "terms": {
                        "field": "_type",
                        "size": 0
                    }
                }
            }
        },
        "earlier_documents": {
            "filter": {
                "range": {
                    "providerUpdatedDateTime": {
                        "lt": three_months_ago
                    }
                }
            },
            "aggs": {
                "sources": {
                    "terms": {
                        "field": "_type",
                        "size": 0,
                        "min_doc_count": 0
                    }
                }
            }
        }
    }
    date_histogram_query = {
        'query': {
            'filtered': {
                'query': query['query'],
                'filter': {
                    'range': {
                        'providerUpdatedDateTime': {
                            'gt': three_months_ago
                        }
                    }
                }
            }
        }
    }
    date_histogram_query['aggs'] = {
        "date_chunks": {
            "terms": {
                "field": "_type",
                "size": 0,
                "exclude": "of|and|or"
            },
            "aggs": {
                "articles_over_time": {
                    "date_histogram": {
                        "field": "providerUpdatedDateTime",
                        "interval": "week",
                        "min_doc_count": 0,
                        "extended_bounds": {
                            "min": three_months_ago,
                            "max": timegm(gmtime()) * 1000
                        }
                    }
                }
            }
        }
    }

    results = share_es.search(index=index,
                              body=query)
    date_results = share_es.search(index=index,
                                   body=date_histogram_query)
    results['aggregations']['date_chunks'] = date_results['aggregations']['date_chunks']

    chart_results = data_for_charts(results)
    return chart_results


def data_for_charts(elastic_results):
    source_data = elastic_results['aggregations']['sources']['buckets']
    for_charts = {}

    ## for the donut graph list of many lists, source and count
    source_and_counts = [[item['key'], item['doc_count']] for item in source_data]
    for_charts['shareDonutGraph'] = source_and_counts

    r = generate_color()
    stats = {}
    colors = {}
    for bucket in elastic_results['aggregations']['sources']['buckets']:
        stats[bucket['key']] = {
            'doc_count': bucket['doc_count'],
        }
        colors[bucket['key']] = r.next()

    for bucket in elastic_results['aggregations']['earlier_documents']['sources']['buckets']:
        stats[bucket['key']]['earlier_documents'] = bucket['doc_count']

    default_buckets = []
    for bucket in elastic_results['aggregations']['date_chunks']['buckets']:
        default_buckets = bucket['articles_over_time']['buckets']
        stats[bucket['key']]['articles_over_time'] = bucket['articles_over_time']['buckets']

    max_len = 0
    for key, value in stats.iteritems():
        if not stats[key].get('earlier_documents'):
            stats[key]['earlier_documents'] = 0
        if not stats[key].get('articles_over_time'):
            stats[key]['articles_over_time'] = [
                {
                    'key_as_string': item['key_as_string'],
                    'key': item['key'],
                    'doc_count': 0
                }
                for item in default_buckets
            ]
        if len(stats[key]['articles_over_time']) > max_len:
                max_len = len(stats[key]['articles_over_time'])

    names = ['x']
    numbers = [['x']]
    for date in stats[stats.keys()[0]]['articles_over_time']:
        numbers[0].append(' ')

    for key, value in stats.iteritems():
        try:
            names.append(key)
            x = [item['doc_count'] for item in value['articles_over_time']]
            if len(x) < max_len:
                x += [0] * (max_len - len(x))
            x[0] += stats[key].get('earlier_documents', 0)
            numbers.append([key] + [sum(x[0:i + 1]) for i in range(len(x[0:]))])
        except IndexError:
            pass

    date_totals = {
        'date_numbers': numbers,
        'group_names': names
    }

    if date_totals.get('date_numbers') == [[u'x']]:
        for name in date_totals.get('group_names'):
            date_totals.get('date_numbers').append([name, 0])

    for_charts['date_totals'] = date_totals

    all_data = {}
    all_data['raw_aggregations'] = elastic_results['aggregations']

    all_data['charts'] = {
        'shareDonutGraph': {
            'type': 'donut',
            'columns': for_charts['shareDonutGraph'],
            'colors': colors
        },
        'shareTimeGraph': {
            'x': 'x',
            'type': 'area-spline',
            'columns': for_charts['date_totals']['date_numbers'],
            'groups': [for_charts['date_totals']['group_names']],
            'colors': colors
        }
    }

    return all_data


def to_atom(result):
    return {
        'title': html_and_illegal_unicode_replace(result.get('title')) or 'No title provided.',
        'summary': html_and_illegal_unicode_replace(result.get('description')) or 'No summary provided.',
        'id': result['uris']['canonicalUri'],
        'updated': get_date_updated(result),
        'links': [
            {'href': result['uris']['canonicalUri'], 'rel': 'alternate'}
        ],
        'author': format_contributors_for_atom(result['contributors']),
        'categories': [{"term": html_and_illegal_unicode_replace(tag)} for tag in (result.get('tags', []) + result.get('subjects', []))],
        'published': parse(result.get('providerUpdatedDateTime'))
    }


def format_contributors_for_atom(contributors_list):
    return [
        {
            'name': html_and_illegal_unicode_replace(entry['name'])
        } for entry in contributors_list
    ]


def get_date_updated(result):
    try:
        updated = pytz.utc.localize(parse(result.get('providerUpdatedDateTime')))
    except ValueError:
        updated = parse(result.get('providerUpdatedDateTime'))

    return updated
