from website import settings
import logging


# Abstracts search away from solr
logger = logging.getLogger(__name__)

if settings.SEARCH_ENGINE == 'solr':
    import solr_search as search_engine
elif settings.SEARCH_ENGINE == 'elastic':
    import elastic_search as search_engine
else:
    logger.warn("Neither elastic or solr are set to load")


def search(query, start=0):
    result, tags, total = search_engine.search(query, start)
    return result, tags, total

def update_node(node):
    search_engine.update_node(node)

def update_user(user):
    search_engine.update_user(user)

def delete_all():
    search_engine.delete_all()

def search_contributor(query, exclude=None):
    result= search_engine.search_contributor(query, exclude)
    return result
