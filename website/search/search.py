import solr_search
import elastic_search 
from website import settings
import logging


# TODO(fabianvf)
# Abstracts search away from solr
logger = logging.getLogger(__name__)
SOLR = False
ELASTIC = False

if settings.SEARCH_ENGINE == 'all':
    SOLR = True
    ELASTIC = True
elif settings.SEARCH_ENGINE == 'solr':
    SOLR = True
elif settings.SEARCH_ENGINE == 'elastic':
    ELASTIC = True


def search(query, start=0):
    if SOLR: 
        # solr search
#        result, highlight, spellcheck_result  =solr_search.search(query, start=0)
        result, total = solr_search.search(query, start=0)
    if ELASTIC:
        # elastic search
        result2, total2 = elastic_search.search(query, start=0)
    return result2[0], result2[1], total2#, highlight, spellcheck_result #TODO(fabianvf)

def update_node(node):
    if SOLR:
        solr_search.update_node(node)
    if ELASTIC:
        elastic_search.update_node(node)

def update_user(user):
    if SOLR:
        solr_search.update_user(user)
    if ELASTIC:
        elastic_search.update_user(user)

def delete_all():
    if SOLR:
        solr_search.delete_all()
    if ELASTIC:
        elastic_search.delete_all()

def search_contributer():
    if SOLR:
        solr_search.search_contributer()
    if ELASTIC:
        solr_search.search_contributer()
