# -*- coding: utf-8 -*-

from __future__ import division

import re
import copy
import math
import logging
import unicodedata

import six

import pyelasticsearch

from requests.exceptions import ConnectionError

from framework import sentry

from website import settings
from website.filters import gravatar
from website.models import User, Node
from website.search import exceptions
from website.search.util import build_query

logger = logging.getLogger(__name__)


# These are the doc_types that exist in the search database
ALIASES = {
    'project': 'Projects',
    'component': 'Components',
    'registration': 'Registrations',
    'user': 'Users',
    'total': 'Total'
}

INDICES = ['website']

try:
    elastic = pyelasticsearch.ElasticSearch(
        settings.ELASTIC_URI,
        timeout=settings.ELASTIC_TIMEOUT
    )
    logging.getLogger('pyelasticsearch').setLevel(logging.WARN)
    logging.getLogger('requests').setLevel(logging.WARN)
    elastic.health()
except ConnectionError as e:
    sentry.log_exception()
    sentry.log_message("The SEARCH_ENGINE setting is set to 'elastic', but there "
            "was a problem starting the elasticsearch interface. Is "
            "elasticsearch running?")
    elastic = None


def requires_search(func):
    def wrapped(*args, **kwargs):
        if elastic is not None:
            try:
                return func(*args, **kwargs)
            except ConnectionError:
                raise exceptions.SearchUnavailableError('Could not connect to elasticsearch')
            except pyelasticsearch.exceptions.ElasticHttpNotFoundError as e:
                raise exceptions.IndexNotFoundError(e.error)
            except pyelasticsearch.exceptions.ElasticHttpError as e:
                if 'ParseException' in e.error:
                    raise exceptions.MalformedQueryError(e.error)
                raise exceptions.SearchException(e.error)

        sentry.log_message('Elastic search action failed. Is elasticsearch running?')
        raise exceptions.SearchUnavailableError("Failed to connect to elasticsearch")
    return wrapped


@requires_search
def get_counts(count_query, clean=True):
    count_query['aggs'] = {
        'counts': {
            'terms': {
                'field': '_type',
            }
        }
    }
    #pyelastic search is dumb
    res = elastic.send_request('GET', ['_all', '_search'], body=count_query, query_params={'search_type': 'count'})

    counts = {x['key']: x['doc_count'] for x in res['aggregations']['counts']['buckets'] if x['key'] in ALIASES.keys()}

    counts['total'] = sum([val for val in counts.values()])

    return counts


@requires_search
def get_tags(query, index):
    query['aggregations'] = {
        'tag_cloud': {
            'terms': {'field': 'tags'}
        }
    }

    results = elastic.search(query, index=index, doc_type='_all')
    tags = results['aggregations']['tag_cloud']['buckets']

    return tags


@requires_search
def search(query, index='website', search_type='_all'):
    """Search for a query

    :param query: The substring of the username/project name/tag to search for
    :param index:
    :param search_type:

    :return: List of dictionaries, each containing the results, counts, tags and typeAliases
        results: All results returned by the query, that are within the index and search type
        counts: A dictionary in which keys are types and values are counts for that type, e.g, count['total'] is the sum of the other counts
        tags: A list of tags that are returned by the search query
        typeAliases: the doc_types that exist in the search database
    """
    tag_query = copy.deepcopy(query)
    count_query = copy.deepcopy(query)

    for key in ['from', 'size', 'sort']:
        try:
            del tag_query[key]
            del count_query[key]
        except KeyError:
            pass

    tags = get_tags(tag_query, index)
    counts = get_counts(count_query, index)

    # Run the real query and get the results
    raw_results = elastic.search(query, index=index, doc_type=search_type)

    results = [hit['_source'] for hit in raw_results['hits']['hits']]
    return_value = {
        'results': format_results(results),
        'counts': counts,
        'tags': tags,
        'typeAliases': ALIASES
    }
    return return_value


def format_results(results):
    ret = []
    for result in results:
        if result.get('category') == 'user':
            result['url'] = '/profile/' + result['id']
        elif result.get('category') in {'project', 'component', 'registration'}:
            result = format_result(result, result.get('parent_id'))
        ret.append(result)
    return ret


def format_result(result, parent_id=None):
    parent_info = load_parent(parent_id)
    formatted_result = {
        'contributors': result['contributors'],
        'wiki_link': result['url'] + 'wiki/',
        'title': result['title'],
        'url': result['url'],
        'is_component': False if parent_info is None else True,
        'parent_title': parent_info.get('title') if parent_info is not None else None,
        'parent_url': parent_info.get('url') if parent_info is not None else None,
        'tags': result['tags'],
        'contributors_url': result['contributors_url'],
        'is_registration': (result['is_registration'] if parent_info is None
                                                        else parent_info.get('is_registration')),
        'description': result['description'] if parent_info is None else None,
        'category': result.get('category')
    }

    return formatted_result


def load_parent(parent_id):
    parent = Node.load(parent_id)
    if parent is None:
        return None
    parent_info = {}
    if parent is not None and parent.is_public:
        parent_info['title'] = parent.title
        parent_info['url'] = parent.url
        parent_info['is_registration'] = parent.is_registration
        parent_info['id'] = parent._id
    else:
        parent_info['title'] = '-- private project --'
        parent_info['url'] = ''
        parent_info['is_registration'] = None
        parent_info['id'] = None
    return parent_info


@requires_search
def update_node(node, index='website'):
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
        try:
            normalized_title = six.u(node.title)
        except TypeError:
            normalized_title = node.title
        normalized_title = unicodedata.normalize('NFKD', normalized_title).encode('ascii', 'ignore')

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
            'normalized_title': normalized_title,
            'category': category,
            'public': node.is_public,
            'tags': [tag._id for tag in node.tags if tag],
            'description': node.description,
            'url': node.url,
            'is_registration': node.is_registration,
            'registered_date': str(node.registered_date)[:10],
            'wikis': {},
            'parent_id': parent_id,
            'iso_timestamp': node.date_created,
            'boost': int(not node.is_registration) + 1,  # This is for making registered projects less relevant
        }
        for wiki in [
            NodeWikiPage.load(x)
            for x in node.wiki_pages_current.values()
        ]:
            elastic_document['wikis'][wiki.page_name] = wiki.raw_text(node)

        try:
            elastic.update(index, category, id=elastic_document_id, doc=elastic_document, upsert=elastic_document, refresh=True)
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
            elastic.index(index, category, doc=elastic_document, id=elastic_document_id, overwrite_existing=True, refresh=True)

def generate_social_links(social):
    social_links = {}
    if 'github' in social:
        social_links['github'] = 'http://github.com/{}'.format(social['github']) if social['github'] else None
    if 'impactStory' in social:
        social_links['impactStory'] = 'https://impactstory.org/{}'.format(social['impactStory']) if social['impactStory'] else None
    if 'linkedIn' in social:
        social_links['linkedIn'] = 'https://www.linkedin.com/profile/view?id={}'.format(social['linkedIn']) if social['linkedIn'] else None
    if 'orcid' in social:
        social_links['orcid'] = 'http://orcid.com/{}'.format(social['orcid']) if social['orcid'] else None
    if 'personal' in social:
        social_links['personal'] = social['personal'] if social['personal'] else None
    if 'researcherId' in social:
        social_links['researcherId'] = 'http://researcherid.com/rid/{}'.format(social['researcherId']) if social['researcherId'] else None
    if 'scholar' in social:
        social_links['scholar'] = 'http://scholar.google.com/citations?user={}'.format(social['scholar']) if social['scholar'] else None
    if 'twitter' in social:
        social_links['twitter'] = 'http://twitter.com/{}'.format(social['twitter']) if social['twitter'] else None
    return social_links

@requires_search
def update_user(user):
    if not user.is_active():
        try:
            elastic.delete('website', 'user', user._id, refresh=True)
            logger.debug('User ' + user._id + ' successfully removed from the Elasticsearch index')
        except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
            logger.warn('User ' + user._id + 'not in the Elasticsearch index')
        return

    try:
        normalized_name = six.u(user.fullname)
    except TypeError:
        normalized_name = user.fullname
    normalized_name = unicodedata.normalize('NFKD', normalized_name).encode('ascii', 'ignore')

    user_doc = {
        'id': user._id,
        'user': user.fullname,
        'normalized_user': normalized_name,
        'job': user.jobs[0]['institution'] if user.jobs else '',
        'job_title': user.jobs[0]['title'] if user.jobs else '',
        'school': user.schools[0]['institution'] if user.schools else '',
        'category': 'user',
        'degree': user.schools[0]['degree'] if user.schools else '',
        'social': generate_social_links(user.social),
        'boost': 2,  # TODO(fabianvf): Probably should make this a constant or something
    }

    try:
        elastic.update('website', 'user', doc=user_doc, id=user._id, upsert=user_doc, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        elastic.index('website', 'user', id=user._id, doc=user_doc, upsert=user_doc, refresh=True)


@requires_search
def delete_all():
    for idx in INDICES:
        delete_index(idx)


@requires_search
def delete_index(index):
    try:
        elastic.delete_index(index)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        logger.debug('Index {} does not exist; was unable to delete'.format(index))


@requires_search
def create_index():
    '''Creates index with some specified mappings to begin with,
    all of which are applied to all projects, components, and registrations'''
    mapping = {
        'properties': {
            'tags': {
                'type': 'string',
                'index': 'not_analyzed',
            },
        }
    }
    try:
        elastic.create_index('website')
        for type_ in ['project', 'component', 'registration', 'user']:
            elastic.put_mapping('website', type_, mapping)
    except pyelasticsearch.exceptions.IndexAlreadyExistsError:
        pass  # No harm done


@requires_search
def delete_doc(elastic_document_id, node, index='website'):
    category = 'registration' if node.is_registration else node.project_or_component
    try:
        elastic.delete(index, category, elastic_document_id, refresh=True)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        logger.debug('Document {} does not exist; was unable to delete'.format(elastic_document_id))


@requires_search
def search_contributor(query, page=0, size=10, exclude=[], current_user=None):
    """Search for contributors to add to a project using elastic search. Request must
    include JSON data with a "query" field.

    :param query: The substring of the username to search for
    :param page: For pagination, the page number to use for results
    :param size: For pagination, the number of results per page
    :param exclude: A list of User objects to exclude from the search
    :param current_user: A User object of the current user

    :return: List of dictionaries, each containing the ID, full name,
        most recent employment and education, gravatar URL of an OSF user

    """
    start = (page * size)
    items = re.split(r'[\s-]+', query)
    query = ''

    query = "  AND ".join('{}*~'.format(item) for item in items) + \
            "".join(' NOT "{}"'.format(excluded) for excluded in exclude)

    results = search(build_query(query, start=start, size=size), index='website', search_type='user')
    docs = results['results']
    pages = math.ceil(results['counts'].get('user', 0) / size)

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

    return \
        {
            'users': users,
            'total': results['counts']['total'],
            'pages': pages,
            'page': page,
        }
