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
def search(query, index=None, doc_type=None):
    index = index or settings.ELASTIC_INDEX
    return search_engine.search(query, index=index, doc_type=doc_type)

@requires_search
def update_node(node, index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.update_node(node, index=index)


@requires_search
def update_files(node, index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.update_node(node, index=None)

@requires_search
def delete_node(node, index=None):
    index = index or settings.ELASTIC_INDEX
    doc_type = node.project_or_component
    if node.is_registration:
        doc_type = 'registration'
    search_engine.delete_doc(node._id, node, index=index, category=doc_type)


@requires_search
def update_user(user, index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.update_user(user, index=index)


@requires_search
def delete_all():
    search_engine.delete_all()

@requires_search
def delete_index(index):
    search_engine.delete_index(index)

@requires_search
def create_index(index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.create_index(index=index)


@requires_search
def search_contributor(query, page=0, size=10, exclude=[], current_user=None):
    result = search_engine.search_contributor(query=query, page=page, size=size,
                                              exclude=exclude, current_user=current_user)
    return result

def search_share(query, raw=False, index='share'):
    return share_search.search(query, raw=raw, index=index)

def count_share(query, index='share'):
    return share_search.count(query, index=index)

def share_stats(query=None):
    query = query or {}
    return share_search.stats(query=query)

def share_providers():
    return share_search.providers()
