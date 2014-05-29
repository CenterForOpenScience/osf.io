from website import settings
import logging
import pyelasticsearch

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
        

def search(query, start=0):
    return False
    # raise NotImplementedError

def update_node(node):
    from website.addons.wiki.model import NodeWikiPage

    if not (settings.SEARCH_ENGINE in ['elastic', 'all']):
        return

    if node.category =='project':
        elastic_document_id = node._id
    else:
        try:
            elastic_document_id = node.parent_id
            index = 'component'
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
        elastic.index('website', node.category, elastic_document, elastic_document_id)


def update_user(user):
    elastic.index("website", "user",{
        'id' : user._id, 
        'user' : user.fullname
        })
#    raise NotImplementedError

def delete_all():
    return 
#    raise NotImplementedError

def delete_doc(elastic_document_id, node_id):
    return
    #    raise NotImplementedError
