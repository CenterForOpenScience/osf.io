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

def search(query):
    # Run the real query and get the results
    raw_results = share_es.search(index='share', doc_type=None, body=query)

    results = [hit['_source'] for hit in raw_results['hits']['hits']]
    return {
        'results': results,
        'count': raw_results['hits']['total'],
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
                "exclude": "of|and|or"
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
                        "interval": "month",
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
    for_charts['donut_chart'] = source_and_counts

    all_date_data = []
    # for the date aggregations
    chunk_data = elastic_results['aggregations']['date_chunks']['buckets']
    date_names = ['x']
    for entry in chunk_data[0]['articles_over_time']['buckets']:
        date_names.append(entry['key_as_string'].replace('T00:00:00.000Z', ''))

    all_date_data.append(date_names)

    all_source_names = []
    for bucket in chunk_data:
        provider_row = [bucket['key']]
        all_source_names.append(bucket['key'])
        for internal in bucket['articles_over_time']['buckets']:
            provider_row.append(internal['doc_count'])
        provider_cumulative = [sum(provider_row[1:i+2]) for i in range(len(provider_row[1:]))]
        provider_cumulative = [bucket['key']] + provider_cumulative
        all_date_data.append(provider_cumulative)

    for_charts['date_totals'] = {}
    for_charts['date_totals']['date_numbers'] = all_date_data
    for_charts['date_totals']['group_names'] = ['x'] + all_source_names

    all_data = {}
    all_data['raw_aggregations'] = elastic_results['aggregations']
    all_data['for_charts'] = for_charts

    return all_data
