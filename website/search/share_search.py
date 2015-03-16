from time import gmtime
from calendar import timegm
from datetime import datetime

from dateutil.relativedelta import relativedelta

from elasticsearch import Elasticsearch

from website import settings

share_es = Elasticsearch(
    settings.SHARE_ELASTIC_URI,
    request_timeout=settings.ELASTIC_TIMEOUT
)

def search(query, raw=False):
    # Run the real query and get the results
    results = share_es.search(index='share', doc_type=None, body=query)

    return results if raw else {
        'results': [hit['_source'] for hit in results['hits']['hits']],
        'count': results['hits']['total'],
    }


def count(query):
    if query.get('from') is not None:
        del query['from']
    if query.get('size') is not None:
        del query['size']

    count = share_es.count(index='share', body=query)

    return {
        'results': [],
        'count': count['count']
    }


def stats(query=None):
    query = query or {"query": {"match_all": {}}}
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
                    "dateUpdated": {
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
                        'dateUpdated': {
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
                        "field": "dateUpdated",
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

    results = share_es.search(index='share', body=query)
    date_results = share_es.search(index='share', body=date_histogram_query)
    results['aggregations']['date_chunks'] = date_results['aggregations']['date_chunks']

    chart_results = data_for_charts(results)
    return chart_results


def data_for_charts(elastic_results):
    source_data = elastic_results['aggregations']['sources']['buckets']
    for_charts = {}

    ## for the donut graph list of many lists, source and count
    source_and_counts = [[item['key'], item['doc_count']] for item in source_data]
    for_charts['shareDonutGraph'] = source_and_counts

    stats = {}
    for bucket in elastic_results['aggregations']['sources']['buckets']:
        stats[bucket['key']] = {
            'doc_count': bucket['doc_count'],
        }

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

    for_charts['date_totals'] = date_totals

    all_data = {}
    all_data['raw_aggregations'] = elastic_results['aggregations']

    all_data['charts'] = {
        'shareDonutGraph': {
            'type': 'donut',
            'columns': for_charts['shareDonutGraph']
        },
        'shareTimeGraph': {
            'x': 'x',
            'type': 'area-spline',
            'columns': for_charts['date_totals']['date_numbers'],
            'groups': [for_charts['date_totals']['group_names']]
        }
    }

    return all_data
