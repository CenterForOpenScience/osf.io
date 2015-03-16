import logging

from website import settings
from website.search import share_search

logger = logging.getLogger(__name__)

if settings.SEARCH_ENGINE == 'elastic':
    import elastic_search as search_engine
else:
    search_engine = None
    logger.warn('Elastic search is not set to load')


def requires_search(func):
    def wrapped(*args, **kwargs):
        if search_engine is not None:
            return func(*args, **kwargs)
    return wrapped


@requires_search
def search(query, index='website', doc_type=None):
    return search_engine.search(query, index=index, doc_type=doc_type)

@requires_search
def update_node(node, index='website'):
    search_engine.update_node(node)


@requires_search
def update_user(user):
    search_engine.update_user(user)


@requires_search
def delete_all():
    search_engine.delete_all()

@requires_search
def delete_index(index):
    search_engine.delete_index(index)

@requires_search
def create_index():
    search_engine.create_index()


@requires_search
def search_contributor(query, page=0, size=10, exclude=[], current_user=None):
    result = search_engine.search_contributor(query=query, page=page, size=size,
                                              exclude=exclude, current_user=current_user)
    return result

def search_share(query, raw=False):
    return share_search.search(query, raw=raw)

def count_share(query):
    return share_search.count(query)

def share_stats(query=None):
    query = query or {}
    return share_search.stats(query=query)
