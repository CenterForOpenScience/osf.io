# -*- coding: utf-8 -*-

import logging
import pyelasticsearch
import re
import copy

from website import settings
from website.filters import gravatar
from website.models import User, Node

logger = logging.getLogger(__name__)


# These are the doc_types that exist in the search database
TYPES = ['project', 'component', 'user', 'registration']

try:
    elastic = pyelasticsearch.ElasticSearch(
        settings.ELASTIC_URI,
        timeout=settings.ELASTIC_TIMEOUT
    )
    logging.getLogger('pyelasticsearch').setLevel(logging.WARN)
    logging.getLogger('requests').setLevel(logging.WARN)
    elastic.health()
except pyelasticsearch.exceptions.ConnectionError as e:
    logger.error(e)
    logger.warn("The SEARCH_ENGINE setting is set to 'elastic', but there "
                "was a problem starting the elasticsearch interface. Is "
                "elasticsearch running?")
    elastic = None


def search(raw_query, start=0):
    orig_query = raw_query

    query, filtered_query = _build_query(raw_query, start)

    # Get document counts by type
    counts = {}
    count_query = copy.deepcopy(query)
    del count_query['from']
    del count_query['size']
    for type in TYPES:
        try:
            count_query['query']['function_score']['query']['filtered']['filter']['type']['value'] = type
        except KeyError:
            pass

        counts[type + 's'] = elastic.count(count_query, index='website', doc_type=type)['count']

    # Figure out which count we should display as a total
    for type in TYPES:
        if type + ':' in orig_query:
            counts['total'] = counts[type + 's']
    if not counts.get('total'):
        counts['total'] = sum([x for x in counts.values()])

    # Run the real query and get the results
    raw_results = elastic.search(query, index='website')
    results = [hit['_source'] for hit in raw_results['hits']['hits']]
    formatted_results, tags = create_result(results, counts)

    return formatted_results, tags, counts


def _build_query(raw_query, start=0):

    # Default to searching all types with a big 'or' query
    type_filter = {}
    type_filter['or'] = [{
        'type': {
            'value': type
        }
    } for type in TYPES]

    # But make sure to filter by type if requested
    for type in TYPES:
        if type + ':' in raw_query:
            type_filter = {
                'type': {
                    'value': type
                }
            }

    # Cleanup string before using it to query
    for type in TYPES:
        raw_query = raw_query.replace(type + ':', '')

    raw_query = raw_query.replace('(', '').replace(')', '').replace('\\', '').replace('"', '')

    raw_query = raw_query.replace(',', ' ').replace('-', ' ').replace('_', ' ')

    # If the search contains wildcards, make them mean something
    if '*' in raw_query:
        inner_query = {
            'query_string': {
                'default_field': '_all',
                'query': raw_query + '*',
                'analyze_wildcard': True,
            }
        }
    else:
        inner_query = {
            'multi_match': {
                'query': raw_query,
                'type': 'phrase_prefix',
                'fields': '_all',
            }
        }

    # If the search has a tag filter, add that to the query
    if 'tags:' in raw_query:
        tags = raw_query.replace('AND', ' ').split('tags:')
        tag_filter = {
            'query': {
                'match': {
                    'tags': {
                        'query': '',
                        'operator': 'or'
                    }
                }
            }
        }
        for i in range(1, len(tags)):
            for tag in tags[i].split():
                tag_filter['query']['match']['tags']['query'] += ' ' + tag

        # If the query is empty, turn it back to a wildcard search
        if not tags[0].strip():
            inner_query = {
                'query_string': {
                    'default_field': '_all',
                    'query': '*',
                    'analyze_wildcard': True,
                }
            }
        elif inner_query.get('query_string'):
            inner_query['query_string']['query'] = tags[0]
        elif inner_query.get('multi_match'):
            inner_query['multi_match']['query'] = tags[0]

        inner_query = {
            'filtered': {
                'filter': tag_filter,
                'query': inner_query
            }
        }

    # This is the complete query
    query = {
        'query': {
            'function_score': {
                'query': {
                    'filtered': {
                        'filter': type_filter,
                        'query': inner_query
                    }
                },
                'functions': [{
                    'field_value_factor': {
                        'field': 'boost'
                    }
                }],
                'score_mode': 'multiply'
            }
        },
        'from': start,
        'size': 10,
    }

    return query, raw_query


def update_node(node):
    from website.addons.wiki.model import NodeWikiPage

    component_categories = ['', 'hypothesis', 'methods and measures', 'procedure', 'instrumentation', 'data', 'analysis', 'communication', 'other']
    category = 'component' if node.category in component_categories else node.category

    if category == 'project':
        elastic_document_id = node._id
        parent_id = None
        category = 'registration' if node.is_registration else category
    else:
        try:
            elastic_document_id = node._id
            parent_id = node.parent_id
            category = 'registration' if node.is_registration else category
        except IndexError:
            # Skip orphaned components
            return
    if node.is_deleted or not node.is_public:
        delete_doc(elastic_document_id, node)
    else:
        elastic_document = {
            'id': elastic_document_id,
            'contributors': [
                x.fullname for x in node.visible_contributors
                if x is not None
                and x.is_active()
            ],
            'contributors_url': [
                x.profile_url for x in node.visible_contributors
                if x is not None
                and x.is_active()
            ],
            'title': node.title,
            'category': node.category,
            'public': node.is_public,
            'tags': [tag._id for tag in node.tags if tag],
            'description': node.description,
            'url': node.url,
            'registeredproject': node.is_registration,
            'wikis': {},
            'parent_id': parent_id,
            'boost': int(not node.is_registration) + 1,  # This is for making registered projects less relevant
        }
        for wiki in [
            NodeWikiPage.load(x)
            for x in node.wiki_pages_current.values()
        ]:
            elastic_document['wikis'][wiki.page_name] = wiki.raw_text(node)

        try:
            elastic.update('website', category, id=elastic_document_id, doc=elastic_document, upsert=elastic_document, refresh=True)
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
            elastic.index('website', category, elastic_document, id=elastic_document_id, overwrite_existing=True, refresh=True)


def update_user(user):
    if not user.is_active():
        try:
            elastic.delete('website', 'user', user._id, refresh=True)
            logger.debug('User ' + user._id + ' successfully removed from the Elasticsearch index')
            return
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError as e:
            logger.error(e)
            return

    user_doc = {
        'id': user._id,
        'user': user.fullname,
        'boost': 2,  # TODO(fabianvf): Probably should make this a constant or something
    }

    try:
        elastic.update('website', 'user', doc=user_doc, id=user._id, upsert=user_doc, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        elastic.index("website", "user", user_doc, id=user._id, overwrite_existing=True, refresh=True)


def delete_all():
    try:
        elastic.delete_index('website')
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError as e:
        logger.error(e)
        logger.error("The index 'website' was not deleted from elasticsearch")


def delete_doc(elastic_document_id, node):
    category = 'registration' if node.is_registration else node.project_or_component
    try:
        elastic.delete('website', category, elastic_document_id, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        logger.warn("Document with id {} not found in database".format(elastic_document_id))


def _load_parent(parent):
    parent_info = {}
    if parent is not None and parent.is_public:
        parent_info['title'] = parent.title
        parent_info['url'] = parent.url
        parent_info['wiki_url'] = parent.url + 'wiki/'
        parent_info['contributors'] = [
            contributor.fullname
            for contributor in parent.visible_contributors
        ]
        parent_info['tags'] = [tag._id for tag in parent.tags]
        parent_info['contributors_url'] = [
            contributor.url
            for contributor in parent.visible_contributors
        ]
        parent_info['is_registration'] = parent.is_registration
        parent_info['description'] = parent.description
        parent_info['id'] = parent._id
    else:
        parent_info['title'] = '-- private project --'
        parent_info['url'] = ''
        parent_info['wiki_url'] = ''
        parent_info['contributors'] = []
        parent_info['tags'] = []
        parent_info['contributors_url'] = []
        parent_info['is_registration'] = None
        parent_info['description'] = ''
        parent_info['id'] = None
    return parent_info


def create_result(results, counts):
    ''' Takes a dict of counts by type, and a list of dicts of the following structure:
    {
        'category': {NODE CATEGORY},
        'description': {NODE DESCRIPTION},
        'contributors': [{LIST OF CONTRIBUTORS}],
        'title': {TITLE TEXT},
        'url': {URL FOR NODE},
        'tags': {LIST OF TAGS},
        'contributors_url': [{LIST OF LINKS TO CONTRIBUTOR PAGES}],
        'id': {NODE ID},
        'parent_id': {PARENT NODE ID},
        'parent_title': {TITLE TEXT OF PARENT NODE},
        'wikis': {LIST OF WIKIS AND THEIR TEXT},
        'public': {TRUE OR FALSE},
        'registeredproject': {TRUE OR FALSE}
    }

    Returns list of dicts of the following structure:
    {
        'contributors': [{LIST OF CONTRIBUTORS}],
        'wiki_link': '{LINK TO WIKIS}',
        'title': '{TITLE TEXT}',
        'url': '{URL FOR NODE}',
        'nest': {Nested node attributes},
        'tags': [{LIST OF TAGS}],
        'contributors_url': [{LIST OF LINKS TO CONTRIBUTOR PAGES}],
        'is_registration': {TRUE OR FALSE},
        'highlight': [{No longer used, need to phase out}]
        'description': {PROJECT DESCRIPTION}
    }
    '''
    formatted_results = []
    word_cloud = {}
    visited_nodes = {}  # For making sure projects are only returned once
    num_deleted = 0  # For making deleting projects from the list faster
    index = 0  # For keeping track of what index a project is stored
    for result in results:
        # User results are handled specially
        if 'user' in result:
            formatted_results.append({
                'id': result['id'],
                'user': result['user'],
                'user_url': '/profile/' + result['id'],
            })
            index += 1
        else:
            # Build up word cloud
            for tag in result['tags']:
                word_cloud[tag] = 1 if word_cloud.get(tag) is None \
                    else word_cloud[tag] + 1

            # Ensures that information from private projects is never returned
            parent = Node.load(result['parent_id'])
            parent_info = _load_parent(parent)  # This is to keep track of information, without using the node (for security)

            # Check if parent has already been visited, if so, delete it
            if parent and visited_nodes.get(parent_info['id']):
                for i in range(visited_nodes.get(parent_info['id']) - num_deleted, len(formatted_results)):
                    result_url = formatted_results[i].get('url')
                    if result_url and result_url == parent_info['url']:
                        del formatted_results[i]
                        num_deleted += 1
                        break
                visited_nodes[parent_info['id']] = index
            elif visited_nodes.get(result['id']):
                # If node already visited, it should not be returned as a result
                continue
            elif parent_info['id']:
                visited_nodes[parent_info['id']] = index
            else:
                visited_nodes[result['id']] = index

            # Format dictionary for output
            formatted_results.append(_format_result(result, parent, parent_info))
            index += 1

    return formatted_results, word_cloud


def _format_result(result, parent, parent_info):
    formatted_result = {
        'contributors': result['contributors'] if parent is None
            else parent_info['contributors'],
        'wiki_link': result['url'] + 'wiki/' if parent is None
            else parent_info['wiki_url'],
        'title': result['title'] if parent is None
            else parent_info['title'],
        'url': result['url'] if parent is None else parent_info['url'],
        'nest': {
            result['id']:{#Nested components have all their own attributes
                'title': result['title'],
                'url': result['url'],
                'wiki_link': result['url'] + 'wiki/',
                'contributors': result['contributors'],
                'contributors_url': result['contributors_url'],
                'highlight': [],
                'description': result['description'],
            }
        } if parent is not None else {},
        'tags': result['tags'] if parent is None else parent_info['tags'],
        'contributors_url': result['contributors_url'] if parent is None
            else parent_info['contributors_url'],
        'is_registration': result['registeredproject'] if parent is None
            else parent_info['is_registration'],
        'highlight': [],
        'description': result['description'] if parent is None
            else parent_info['description'],
    }

    return formatted_result


def search_contributor(query, exclude=None, current_user=None):
    """Search for contributors to add to a project using elastic search. Request must
    include JSON data with a "query" field.

    :param: Search query, current_user
    :return: List of dictionaries, each containing the ID, full name,
        most recent employment and education, gravatar URL of an OSF user

    """
    query.replace(" ", "_")
    query = re.sub(r'[\-\+]', '', query)
    query = re.split(r'\s+', query)

    if len(query) > 1:
        and_filter = {'and': []}
        for item in query:
            and_filter['and'].append({
                'prefix': {
                    'user': item.lower()
                }
            })
    else:
        and_filter = {
            'prefix': {
                'user': query[0].lower()
            }
        }

    query = {
        'query': {
            'filtered': {
                'filter': and_filter
            }
        }
    }

    results = elastic.search(query, index='website')
    docs = [hit['_source'] for hit in results['hits']['hits']]

    if exclude:
        docs = (x for x in docs if x.get('id') not in exclude)

    users = []
    for doc in docs:
        # TODO: use utils.serialize_user
        user = User.load(doc['id'])

        if current_user:
            n_projects_in_common = current_user.n_projects_in_common(user)
        else:
            n_projects_in_common = 0

        if user is None:
            logger.error('Could not load user {0}'.format(doc['id']))
            continue
        if user.is_active():  # exclude merged, unregistered, etc.
            current_employment = None
            education = None

            if user.jobs:
                current_employment = user.jobs[0]['institution']

            if user.schools:
                education = user.schools[0]['institution']

            users.append({
                'fullname': doc['user'],
                'id': doc['id'],
                'employment': current_employment,
                'education': education,
                'n_projects_in_common': n_projects_in_common,
                'gravatar_url': gravatar(
                    user,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR,
                ),
                'profile_url': user.profile_url,
                'registered': user.is_registered,
                'active': user.is_active()

            })



    return {'users': users}
