import urllib
import urllib2
import ast

from website import settings
from website.filters import gravatar
from website.models import User
import logging
import sunburnt
from .utils import clean_solr_doc 
import socket

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    solr = sunburnt.SolrInterface(settings.SOLR_URI)
except socket.error as e:
    logger.error(e)
    logger.warn("The SEARCH_ENGINE setting is set to 'solr' but there was a problem ")


def update_node(node):
    """Send the current state of the object to Solr, or delete it from Solr
    as appropriate.
    """
    solr_document={}
    def solr_bool(value):
        """Return a string value for a boolean value that solr will
        correctly serialize.
        """
        return 'true' if value is True else 'false'

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
        delete_doc({
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


def delete_doc(args=None):
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
    #return result, highlight, spellcheck_result
    results, tags = create_result(highlight, result['docs'])
    return results, tags, result['numFound']

def delete_all():
    solr.delete_all()
    solr.commit()

def create_result(highlights, results):
    result_search = []
    tags = {}
    for result in results:
        container = {}
        id = result['id']
        # users are separate documents in our search database,
        # so the logic for returning
        # those documents is different
        if 'user' in result:
            container['id'] = result['id']
            container['user'] = result['user']
            container['user_url'] = '/profile/'+result['id']
            result_search.append(container)
        else:
            container['title'] = result.get(id+'_title', '-- private project --')
            container['url'] = result.get(id+'_url') 
            contributors = []
            contributors_url = []
            # we're only going to show contributors on projects, for now
            for contributor in result.get(id+'_contributors', []): 
                contributors.append(contributor)
            for url in result.get(id+'_contributors_url', []): 
                contributors_url.append(url)
            container['contributors'] = contributors
            container['contributors_url'] = contributors_url
            # highlights will be returned as liss
            main_lit = []
            # we will create the wiki links
            main_wiki_link = ''
            # nest is for our nested nodes; i.e, materials, procedure ects
            nest = {}
            component_tags = []
            # need to keep track of visisted nodes for our tag cloud so we dont
            # miscount our fx of tags
            visited_nests = []
            for key, value in highlights[id].iteritems():
                if id in key:
                    # if wiki is in the key,
                    # we have to split on __ to build the url for the wik
                    if '__wiki' in key:
                        main_wiki_link = result[id+'_url'] + (
                            '/wiki/' + key.split('__')[1])
                    # we're only going to show
                    # the highlight if its wiki or description. title or
                    # tags is redundant information
                    if '__wiki' in key or '_description' in key:
                        main_lit = value
                # if id is not in key, we know that we have some
                # nested information to display
                elif id not in key:
                    if key == 'id':
                        continue
                    # our first step is to get id of the
                    # node by splitting the key
                    # wiki keys are set up to include page name as well.
                    # so splitting to find
                    # the node id is different
                    if '__wiki' in key:
                        splits = key.split('__')
                        split_id = splits[0]
                        pagename = splits[1]
                    else:
                        split_id = key.split('_')[0]
                    # nodes can have contributors
                    contributors = []
                    contributors_url = []
                    lit = []
                    wiki_link = ''
                    # build our wiki link
                    if '__wiki' in key:
                        wiki_link = result[split_id+'_url'] + '/wiki/'+pagename
                    # again title and tags are
                    # redundant so only show highlight if the
                    # wiki or description are in the key
                    if '__wiki' in key or '_description' in key:
                        if value[0] != 'None':
                            lit = value
                    # build our contributor list and our contributor url list
                    for contributor in result.get(split_id+'_contributors', []):
                        contributors.append(contributor)
                    for url in result.get(split_id+'_contributors_url', []):
                        contributors_url.append(url)
                    if result[split_id+'_public']:
                        nest[split_id] = {
                            'title': result[split_id+'_title'],
                            'url': result[split_id+'_url'],
                            'highlight': lit or nest.get(split_id)['highlight'] if nest.get(split_id) else None,
                            'wiki_link': wiki_link,
                            'contributors': contributors,
                            'contributors_url': contributors_url
                        }
                        if split_id+'_tags' in result:
                            if split_id not in visited_nests:
                                # we've visted the node so
                                # append to our visited nests lists
                                visited_nests.append(split_id)
                                # we're going to have a
                                # list of all tags for each project.
                                # we're creating a list with no
                                # duplicates using sets
                                component_tags = component_tags + list(
                                    set(result[split_id+'_tags']) - set(
                                        component_tags))
                                # count the occurence of each tag
                                for tag in result[split_id+'_tags']:
                                    if tag not in tags.keys():
                                        tags[tag] = 1
                                    else:
                                        tags[tag] += 1
            # add the highlight to our dictionary
            if main_lit:
                container['highlight'] = main_lit
            else:
                container['highlight'] = None
            # and the link to the wiki
            container['wiki_link'] = main_wiki_link
            # and our nested information
            container['nest'] = nest
            container['is_registration'] = result.get(
                id + '_registeredproject', 
                False
            )
            if id + '_tags' in result.keys(): 
                # again using sets to create a list without duplicates
                container['tags'] = result[id+'_tags'] + list( 
                    set(component_tags) - set(result[id+'_tags'])) 
                # and were still keeping count of tag occurence
                for tag in result[id+'_tags']: 
                    if tag not in tags.keys():
                        tags[tag] = 1
                    else:
                        tags[tag] += 1
            result_search.append(container)
    return result_search, tags


def search_contributor(query, exclude=None):
    """Search for contributors to add to a project using Solr. Request must
    include JSON data with a "query" field.

    :param: Search query
    :return: List of dictionaries, each containing the ID, full name, and
        gravatar URL of an OSF user

    """
    import re
    # Prepare query
    query = re.sub(r'[\-\+]', ' ', query)

    # Prepend "user:" to each token in the query; else Solr will search for
    # e.g. user:Barack AND Obama. Also search for tokens plus wildcard so that
    # Bar will match Barack. Note: in Solr, Barack* does not match Barack,
    # so must search for (Barack OR Barack*).
    q = ' AND '.join([ 
        u'user:({token} OR {token}*)'.format(token=token).encode('utf-8')
        for token in re.split(r'\s+', query)
    ])

    docs = search(q)[0]

    if exclude:
        docs = (x for x in docs if x.get('id') not in exclude)

    users = []
    for doc in docs:
        # TODO: use utils.serialize_user
        user = User.load(doc['id'])
        if user is None:
            logger.error('Could not load user {0}'.format(doc['id']))
            continue
        if user.is_active():  # exclude merged, unregistered, etc.
            users.append({
                'fullname': doc['user'],
                'email': user.username,
                'id': doc['id'],
                'gravatar_url': gravatar(
                    user,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR,
                ),
                'registered': user.is_registered,
                'active': user.is_active()
            })

    return {'users': users}


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
