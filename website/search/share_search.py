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
    return count['count']
