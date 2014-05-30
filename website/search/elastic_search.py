from website import settings
import logging
import pyelasticsearch
import collections

logger = logging.getLogger(__name__)

if settings.SEARCH_ENGINE in ["elastic", "all"]:
    try:
        elastic = pyelasticsearch.ElasticSearch("http://localhost:9201")
        logging.getLogger('pyelasticsearch').setLevel(logging.DEBUG)
        logging.getLogger('requests').setLevel(logging.DEBUG)
    except Exception as e:
        logger.error(e)
        logger.warn("The SEARCH_ENGINE setting is set to 'elastic', but there"
                "was a problem starting the elasticsearch interface. Is "
                "elasticsearch running?")
        elastic=None
else:
    elastic=None
    logger.warn("Elastic is not set to start")
        

def search(raw_query, start=0):
    def convert(data):
        if isinstance(data, basestring):
            return str(data)
        elif isinstance(data, collections.Mapping):
            return dict(map(convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(convert, data))
        else:
            return data

    query = {
        'query': {
            'match' : {
                '_all': raw_query    
            }
        }
    }
    raw_results = convert(elastic.search(query, index='website'))
    results = {
            'start':0, 
            'numFound':raw_results['hits']['total'], 
            'docs':[hit['_source'] for hit in raw_results['hits']['hits']]
    }
    return results


def update_node(node):
    from website.addons.wiki.model import NodeWikiPage

    if not (settings.SEARCH_ENGINE in ['elastic', 'all']):
        return

    if node.category =='project':
        elastic_document_id = node._id
        category = node.category
    else:
        try:
            elastic_document_id = node.parent_id
            category = 'component'
        except IndexError:
            # Skip orphaned components
            return
    if node.is_deleted or not node.is_public:
        delete_doc(elastic_document_id, node._id)
    else:
        elastic_document = {
            'id': elastic_document_id,
            'contributors': [
                x.fullname for x in node.contributors
                if x is not None
            ],
            'contributors_url': [
                x.profile_url for x in node.contributors
                if x is not None
            ],
            'title': node.title,
            'category': node.category,
            'public': node.is_public,
            'tags': [x._id for x in node.tags],
            'description': node.description,
            'url': node.url,
            'registeredproject': node.is_registration,
        }
        logger.warn(node.category)
        for wiki in [
            NodeWikiPage.load(x)
            for x in node.wiki_pages_current.values()
        ]:
            elastic_document.update({
                '__'.join((node._id, wiki.page_name, 'wiki')): wiki.raw_text
            })
        # check to see if the document is in the elasticsearch database
#TODO(fabianvf)        try:
#            new = solr.query(id=solr_document['id']).execute()[0]
#        except IndexError:
#            new = dict()

#        if elastic_document:
#            new.update(clean_solr_doc(solr_document))
#        solr.add(new)
#        solr.commit()
        elastic.index('website', category, elastic_document, elastic_document_id)


def update_user(user):
    elastic.index("website", "user",{
        'id' : user._id, 
        'user' : user.fullname
        })

def delete_all():
    return 
#    raise NotImplementedError

def delete_doc(elastic_document_id, node_id):
    return
    #    raise NotImplementedError
