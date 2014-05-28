import solr_search
import elastic_search # TODO may be bad form, because elasticsearch is also a module
from website import settings
# TODO
# Abstracts search away from solr

def search(query, start=0):
    if settings.USE_SOLR: #TODO add a specific option in for elastic search as well
        # solr search
        return solr_search.search(query, start=0)
    else:
        # elastic search
        return elastic_search.search(query, start=0)

def update_search(node):
   solr_search.update_solr(node)

def update_user(user):
    solr_search.update_user(user)

def delete_all():
    solr_search.delete_all()
