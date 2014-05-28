from elasticsearch import ElasticSearch
import logging
from website import settings

logger = logging.getLogger(__name__) #TODO need to do something with logger

#TODO need to add setting for elastic search and check it here
if settings.USE_SOLR:
    try:
        es = ElasticSearch() # default port is 9200
    except Exception as e:
        logger.error(e)
        logger.warn("Elastic Search cannot connect. Check that an instance is not already running.")
        es = None
else:
    es = None

def update_elastic(args=None):
    #TODO Call update on document in args['id']
    pass

def migrate_elastic_wiki(args=None):
    #TODO find what this does
    pass

def update_user(user):
    #TODO Call update on user given
    pass

def delete_elastic_doc(args=None):
    #TODO if the document is in the index, remove it
    pass

