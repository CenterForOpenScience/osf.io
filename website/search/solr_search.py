import urllib
import urllib2
import ast

from website import settings
import logging
import sunburnt

from website import settings
from framework.search.utils import clean_solr_doc 


logger = logging.getLogger(__name__)

if settings.USE_SOLR:
    try:
        solr = sunburnt.SolrInterface(settings.SOLR_URI)
    except Exception as e:
        logger.error(e)
        logger.warn("The USE_SOLR setting is enabled but there was a problem "
                    "starting the Solr interface. Is the Solr server running?")
        solr = None
else:
    solr = None

def update_solr(node):
    """Send the current state of the object to Solr, or delete it from Solr
    as appropriate.
    """
    solr_document={}
    def solr_bool(value):
        """Return a string value for a boolean value that solr will
        correctly serialize.
        """
        return 'true' if value is True else 'false'
    if not settings.USE_SOLR:
        return

    from website.addons.wiki.model import NodeWikiPage

    if node.category == 'project':
        # All projects use their own IDs.
        solr_document_id = node._id
    else:
        try:
            # Components must have a project for a parent; use its ID.
            solr_document_id = node.parent_id
        except IndexError:
            # Skip orphaned components. There are some in the DB...
            return
    if node.is_deleted or not node.is_public:
        # If the Node is deleted *or made private*
        # Delete or otherwise ensure the Solr document doesn't exist.
        delete_solr_doc({
            'doc_id': solr_document_id,
            '_id': node._id,
        })
    else:
        # Insert/Update the Solr document
        solr_document = {
            'id': solr_document_id,
            #'public': self.is_public,
            '{}_contributors'.format(node._id): [
                x.fullname for x in node.contributors
                if x is not None
            ],
            '{}_contributors_url'.format(node._id): [
                x.profile_url for x in node.contributors
                if x is not None
            ],
            '{}_title'.format(node._id): node.title,
            '{}_category'.format(node._id): node.category,
            '{}_public'.format(node._id): solr_bool(node.is_public),
            '{}_tags'.format(node._id): [x._id for x in node.tags],
            '{}_description'.format(node._id): node.description,
            '{}_url'.format(node._id): node.url,
            '{}_registeredproject'.format(node._id): solr_bool(node.is_registration),
        }
        # TODO: Move to wiki add-on
        for wiki in [
            NodeWikiPage.load(x)
            for x in node.wiki_pages_current.values()
        ]:
            solr_document.update({
                '__'.join((node._id, wiki.page_name, 'wiki')): wiki.raw_text
            })
        #update_solr(solr_document)#TODO turn this to update_search
        # check to see if the document is in the solr database
        try:
            new = solr.query(id=solr_document['id']).execute()[0]
        except IndexError:
            new = dict()

        if solr_document:
            new.update(clean_solr_doc(solr_document))
        solr.add(new)
        solr.commit()



def migrate_solr_wiki(args=None):
    # migrate wiki function occurs after we migrate
    # projects, so its only relevant for projects and
    # nodes that exist in our database
    if solr.query(id=args['id']).execute():
        db = solr.query(id=args['id']).execute()[0]
        for key, value in args.iteritems():
            if 'wiki' in key:
                db[key] = value
        solr.add(db)
        solr.commit()


def update_user(user):
    # if the user is already there, early return
    solr.add({
        'id': user._id,
        'user': user.fullname,
    })
    solr.commit()


def delete_solr_doc(args=None):
    # if the id we have is for a project, then we
    # just deleted the document
    try:
        db = solr.query(id=args['doc_id']).execute()[0]
        for key in db.keys():
            if key[:len(args['_id'])] == args['_id']:
                del db[key]

        solr.add(db)
        solr.commit()
    except IndexError:
        # Document ID doesn't exist in Solr
        logger.warn('id {} not found in Solr'.format(args['_id']))

def search(query, start=0):
    # here is our query. the default search field is text which maps to tags,
    # description, wiki, and title
    # start is for our pagination
    query_args = {
        'q': query,
        'hl.query': query, 'hl': 'true', 'hl.fl': '*',
        'hl.fragsize': '100', 'hl.snippets': '10',
        'hl.preserveMulti': 'true',
        'spellcheck': 'true', 'spellcheck.collate': 'true',
        'start': start, 'rows': 10}
    import logging
#    logger = logging.getLogger(__name__)
#    logger.warn(query_args)
    encoded_args = urllib.urlencode(_encoded_dict(query_args))
    url = '{}spell?{}&wt=python'.format(settings.SOLR_URI, encoded_args)
    # post to the url
    solrReq = urllib2.Request(url)
    solrReq.add_header('Content-Type', 'application/json')
    solrPost = urllib2.urlopen(solrReq)
    # get our result
    result = ast.literal_eval(solrPost.read())
    # spellcheck (if there is one)
    spellcheck = result['spellcheck']['suggestions'] \
        if 'spellcheck' in result else None
    # highlight
    highlight = result['highlighting']
    # and the list of documents
    result = result['response']
    # look for specllcheck,
    # dont return that public_project was part of the query to the user
    if spellcheck:
        spellcheck_result = spellcheck[-1]
    else:
        spellcheck_result = None
    solrPost.close()
    return result, highlight, spellcheck_result

def delete_all():
    solr.delete_all()
    solr.commit()


def _encoded_dict(in_dict):
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict
