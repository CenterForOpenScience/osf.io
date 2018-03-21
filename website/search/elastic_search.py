
# -*- coding: utf-8 -*-

from __future__ import division

import copy
import functools
import logging
import math
import re
import unicodedata
from framework import sentry

import six

from django.apps import apps
from django.core.paginator import Paginator
from django.db.models import Q
from elasticsearch import (ConnectionError, Elasticsearch, NotFoundError,
                           RequestError, TransportError, helpers)
from framework.celery_tasks import app as celery_app
from framework.database import paginated
from osf.models import AbstractNode
from osf.models import OSFUser
from osf.models import BaseFileNode
from osf.models import Institution
from osf.models import QuickFilesNode
from osf.models import CollectedGuidMetadata
from osf.utils.sanitize import unescape_entities
from website import settings
from website.filters import profile_image_url
from osf.models.licenses import serialize_node_license_record
from website.search import exceptions
from website.search.util import build_query, clean_splitters
from website.views import validate_page_num

logger = logging.getLogger(__name__)


# These are the doc_types that exist in the search database
ALIASES = {
    'project': 'Projects',
    'component': 'Components',
    'registration': 'Registrations',
    'user': 'Users',
    'total': 'All OSF Results',
    'file': 'Files',
    'institution': 'Institutions',
    'preprint': 'Preprints',
    'collectionObject': 'Collection Objects',
}

DOC_TYPE_TO_MODEL = {
    'component': AbstractNode,
    'project': AbstractNode,
    'registration': AbstractNode,
    'user': OSFUser,
    'file': BaseFileNode,
    'institution': Institution,
    'preprint': AbstractNode,
    'collectionObject': CollectedGuidMetadata,
}

# Prevent tokenizing and stop word removal.
NOT_ANALYZED_PROPERTY = {'type': 'string', 'index': 'not_analyzed'}

# Perform stemming on the field it's applied to.
ENGLISH_ANALYZER_PROPERTY = {'type': 'string', 'analyzer': 'english'}

INDEX = settings.ELASTIC_INDEX

CLIENT = None


def client():
    global CLIENT
    if CLIENT is None:
        try:
            CLIENT = Elasticsearch(
                settings.ELASTIC_URI,
                request_timeout=settings.ELASTIC_TIMEOUT,
                retry_on_timeout=True,
                **settings.ELASTIC_KWARGS
            )
            logging.getLogger('elasticsearch').setLevel(logging.WARN)
            logging.getLogger('elasticsearch.trace').setLevel(logging.WARN)
            logging.getLogger('urllib3').setLevel(logging.WARN)
            logging.getLogger('requests').setLevel(logging.WARN)
            CLIENT.cluster.health(wait_for_status='yellow')
        except ConnectionError:
            message = (
                'The SEARCH_ENGINE setting is set to "elastic", but there '
                'was a problem starting the elasticsearch interface. Is '
                'elasticsearch running?'
            )
            if settings.SENTRY_DSN:
                try:
                    sentry.log_exception()
                    sentry.log_message(message)
                except AssertionError:  # App has not yet been initialized
                    logger.exception(message)
            else:
                logger.error(message)
            exit(1)
    return CLIENT


def requires_search(func):
    def wrapped(*args, **kwargs):
        if client() is not None:
            try:
                return func(*args, **kwargs)
            except ConnectionError:
                raise exceptions.SearchUnavailableError('Could not connect to elasticsearch')
            except NotFoundError as e:
                raise exceptions.IndexNotFoundError(e.error)
            except RequestError as e:
                if e.error == 'search_phase_execution_exception':
                    raise exceptions.MalformedQueryError('Failed to parse query')
                if 'ParseException' in e.error:  # ES 1.5
                    raise exceptions.MalformedQueryError(e.error)
                if type(e.error) == dict:  # ES 2.0
                    try:
                        root_cause = e.error['root_cause'][0]
                        if root_cause['type'] == 'query_parsing_exception':
                            raise exceptions.MalformedQueryError(root_cause['reason'])
                    except (AttributeError, KeyError):
                        pass
                raise exceptions.SearchException(e.error)
            except TransportError as e:
                # Catch and wrap generic uncaught ES error codes. TODO: Improve fix for https://openscience.atlassian.net/browse/OSF-4538
                raise exceptions.SearchException(e.error)

        sentry.log_message('Elastic search action failed. Is elasticsearch running?')
        raise exceptions.SearchUnavailableError('Failed to connect to elasticsearch')
    return wrapped


@requires_search
def get_aggregations(query, doc_type):
    query['aggregations'] = {
        'licenses': {
            'terms': {
                'field': 'license.id'
            }
        }
    }

    res = client().search(index=INDEX, doc_type=doc_type, search_type='count', body=query)
    ret = {
        doc_type: {
            item['key']: item['doc_count']
            for item in agg['buckets']
        }
        for doc_type, agg in res['aggregations'].iteritems()
    }
    ret['total'] = res['hits']['total']
    return ret


@requires_search
def get_counts(count_query, clean=True):
    count_query['aggregations'] = {
        'counts': {
            'terms': {
                'field': '_type',
            }
        }
    }

    res = client().search(index=INDEX, doc_type=None, search_type='count', body=count_query)
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

    results = client().search(index=index, doc_type=None, body=query)
    tags = results['aggregations']['tag_cloud']['buckets']

    return tags


@requires_search
def search(query, index=None, doc_type='_all', raw=False):
    """Search for a query

    :param query: The substring of the username/project name/tag to search for
    :param index:
    :param doc_type:

    :return: List of dictionaries, each containing the results, counts, tags and typeAliases
        results: All results returned by the query, that are within the index and search type
        counts: A dictionary in which keys are types and values are counts for that type, e.g, count['total'] is the sum of the other counts
        tags: A list of tags that are returned by the search query
        typeAliases: the doc_types that exist in the search database
    """
    index = index or INDEX
    tag_query = copy.deepcopy(query)
    aggs_query = copy.deepcopy(query)
    count_query = copy.deepcopy(query)

    for key in ['from', 'size', 'sort']:
        try:
            del tag_query[key]
            del aggs_query[key]
            del count_query[key]
        except KeyError:
            pass

    tags = get_tags(tag_query, index)
    try:
        del aggs_query['query']['filtered']['filter']
        del count_query['query']['filtered']['filter']
    except KeyError:
        pass
    aggregations = get_aggregations(aggs_query, doc_type=doc_type)
    counts = get_counts(count_query, index)

    # Run the real query and get the results
    raw_results = client().search(index=index, doc_type=doc_type, body=query)
    results = [hit['_source'] for hit in raw_results['hits']['hits']]

    return_value = {
        'results': raw_results['hits']['hits'] if raw else format_results(results),
        'counts': counts,
        'aggs': aggregations,
        'tags': tags,
        'typeAliases': ALIASES
    }
    return return_value

def format_results(results):
    ret = []
    for result in results:
        if result.get('category') == 'user':
            result['url'] = '/profile/' + result['id']
        elif result.get('category') == 'file':
            parent_info = load_parent(result.get('parent_id'))
            result['parent_url'] = parent_info.get('url') if parent_info else None
            result['parent_title'] = parent_info.get('title') if parent_info else None
        elif result.get('category') in {'project', 'component', 'registration', 'preprint'}:
            result = format_result(result, result.get('parent_id'))
        elif not result.get('category'):
            continue
        ret.append(result)
    return ret

def format_result(result, parent_id=None):
    parent_info = load_parent(parent_id)
    formatted_result = {
        'contributors': result['contributors'],
        'wiki_link': result['url'] + 'wiki/',
        # TODO: Remove unescape_entities when mako html safe comes in
        'title': unescape_entities(result['title']),
        'url': result['url'],
        'is_component': False if parent_info is None else True,
        'parent_title': unescape_entities(parent_info.get('title')) if parent_info else None,
        'parent_url': parent_info.get('url') if parent_info is not None else None,
        'tags': result['tags'],
        'is_registration': (result['is_registration'] if parent_info is None
                                                        else parent_info.get('is_registration')),
        'is_retracted': result['is_retracted'],
        'is_pending_retraction': result['is_pending_retraction'],
        'embargo_end_date': result['embargo_end_date'],
        'is_pending_embargo': result['is_pending_embargo'],
        'description': unescape_entities(result['description']),
        'category': result.get('category'),
        'date_created': result.get('date_created'),
        'date_registered': result.get('registered_date'),
        'n_wikis': len(result['wikis'] or []),
        'license': result.get('license'),
        'affiliated_institutions': result.get('affiliated_institutions'),
        'preprint_url': result.get('preprint_url'),
    }

    return formatted_result


def load_parent(parent_id):
    parent = AbstractNode.load(parent_id)
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


COMPONENT_CATEGORIES = set(settings.NODE_CATEGORY_MAP.keys())

def get_doctype_from_node(node):
    if node.is_registration:
        return 'registration'
    elif node.is_preprint:
        return 'preprint'
    elif node.parent_node is None:
        # ElasticSearch categorizes top-level projects differently than children
        return 'project'
    elif node.category in COMPONENT_CATEGORIES:
        return 'component'
    else:
        return node.category

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_node_async(self, node_id, index=None, bulk=False):
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    try:
        update_node(node=node, index=index, bulk=bulk, async=True)
    except Exception as exc:
        self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_user_async(self, user_id, index=None):
    OSFUser = apps.get_model('osf.OSFUser')
    user = OSFUser.objects.get(id=user_id)
    try:
        update_user(user, index)
    except Exception as exc:
        self.retry(exc)

def serialize_node(node, category):
    NodeWikiPage = apps.get_model('addons_wiki.NodeWikiPage')

    elastic_document = {}
    parent_id = node.parent_id

    try:
        normalized_title = six.u(node.title)
    except TypeError:
        normalized_title = node.title
    normalized_title = unicodedata.normalize('NFKD', normalized_title).encode('ascii', 'ignore')
    elastic_document = {
        'id': node._id,
        'contributors': [
            {
                'fullname': x['fullname'],
                'url': '/{}/'.format(x['guids___id']) if x['is_active'] else None
            }
            for x in node._contributors.filter(contributor__visible=True).order_by('contributor___order')
            .values('fullname', 'guids___id', 'is_active')
        ],
        'title': node.title,
        'normalized_title': normalized_title,
        'category': category,
        'public': node.is_public,
        'tags': list(node.tags.filter(system=False).values_list('name', flat=True)),
        'description': node.description,
        'url': node.url,
        'is_registration': node.is_registration,
        'is_pending_registration': node.is_pending_registration,
        'is_retracted': node.is_retracted,
        'is_pending_retraction': node.is_pending_retraction,
        'embargo_end_date': node.embargo_end_date.strftime('%A, %b. %d, %Y') if node.embargo_end_date else False,
        'is_pending_embargo': node.is_pending_embargo,
        'registered_date': node.registered_date,
        'wikis': {},
        'parent_id': parent_id,
        'date_created': node.created,
        'license': serialize_node_license_record(node.license),
        'affiliated_institutions': list(node.affiliated_institutions.values_list('name', flat=True)),
        'boost': int(not node.is_registration) + 1,  # This is for making registered projects less relevant
        'extra_search_terms': clean_splitters(node.title),
        'preprint_url': node.preprint_url,
    }
    if not node.is_retracted:
        for wiki in NodeWikiPage.objects.filter(guids___id__in=node.wiki_pages_current.values()):
            # '.' is not allowed in field names in ES2
            elastic_document['wikis'][wiki.page_name.replace('.', ' ')] = wiki.raw_text(node)

    return elastic_document

@requires_search
def update_node(node, index=None, bulk=False, async=False):
    from addons.osfstorage.models import OsfStorageFile
    index = index or INDEX
    for file_ in paginated(OsfStorageFile, Q(node=node)):
        update_file(file_, index=index)

    is_qa_node = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(node.tags.all().values_list('name', flat=True))) or any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    if node.is_deleted or not node.is_public or node.archiving or (node.is_spammy and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH) or node.is_quickfiles or is_qa_node:
        delete_doc(node._id, node, index=index)
    else:
        category = get_doctype_from_node(node)
        elastic_document = serialize_node(node, category)
        if bulk:
            return elastic_document
        else:
            client().index(index=index, doc_type=category, id=node._id, body=elastic_document, refresh=True)

def bulk_update_nodes(serialize, nodes, index=None):
    """Updates the list of input projects

    :param function Node-> dict serialize:
    :param Node[] nodes: Projects, components, registrations, or preprints
    :param str index: Index of the nodes
    :return:
    """
    index = index or INDEX
    actions = []
    for node in nodes:
        serialized = serialize(node)
        if serialized:
            actions.append({
                '_op_type': 'update',
                '_index': index,
                '_id': node._id,
                '_type': get_doctype_from_node(node),
                'doc': serialized,
                'doc_as_upsert': True,
            })
    if actions:
        return helpers.bulk(client(), actions)

def serialize_contributors(node):
    return {
        'contributors': [
            {
                'fullname': x['user__fullname'],
                'url': '/{}/'.format(x['user__guids___id'])
            } for x in
            node.contributor_set.filter(visible=True, user__is_active=True).order_by('_order').values('user__fullname', 'user__guids___id')
        ]
    }


bulk_update_contributors = functools.partial(bulk_update_nodes, serialize_contributors)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_contributors_async(self, user_id):
    OSFUser = apps.get_model('osf.OSFUser')
    user = OSFUser.objects.get(id=user_id)
    p = Paginator(user.visible_contributor_to.order_by('id'), 100)
    for page_num in p.page_range:
        bulk_update_contributors(p.page(page_num).object_list)

@requires_search
def update_user(user, index=None):

    index = index or INDEX
    if not user.is_active:
        try:
            client().delete(index=index, doc_type='user', id=user._id, refresh=True, ignore=[404])
            # update files in their quickfiles node if the user has been marked as spam
            if 'spam_confirmed' in user.system_tags:
                quickfiles = QuickFilesNode.objects.get_for_user(user)
                for quickfile_id in quickfiles.files.values_list('_id', flat=True):
                    client().delete(
                        index=index,
                        doc_type='file',
                        id=quickfile_id,
                        refresh=True,
                        ignore=[404]
                    )
        except NotFoundError:
            pass
        return

    names = dict(
        fullname=user.fullname,
        given_name=user.given_name,
        family_name=user.family_name,
        middle_names=user.middle_names,
        suffix=user.suffix
    )

    normalized_names = {}
    for key, val in names.items():
        if val is not None:
            try:
                val = six.u(val)
            except TypeError:
                pass  # This is fine, will only happen in 2.x if val is already unicode
            normalized_names[key] = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')

    user_doc = {
        'id': user._id,
        'user': user.fullname,
        'normalized_user': normalized_names['fullname'],
        'normalized_names': normalized_names,
        'names': names,
        'job': user.jobs[0]['institution'] if user.jobs else '',
        'job_title': user.jobs[0]['title'] if user.jobs else '',
        'all_jobs': [job['institution'] for job in user.jobs[1:]],
        'school': user.schools[0]['institution'] if user.schools else '',
        'all_schools': [school['institution'] for school in user.schools],
        'category': 'user',
        'degree': user.schools[0]['degree'] if user.schools else '',
        'social': user.social_links,
        'boost': 2,  # TODO(fabianvf): Probably should make this a constant or something
    }

    client().index(index=index, doc_type='user', body=user_doc, id=user._id, refresh=True)

@requires_search
def update_file(file_, index=None, delete=False):
    index = index or INDEX

    # TODO: Can remove 'not file_.name' if we remove all base file nodes with name=None
    file_node_is_qa = bool(
        set(settings.DO_NOT_INDEX_LIST['tags']).intersection(file_.tags.all().values_list('name', flat=True))
    ) or bool(
        set(settings.DO_NOT_INDEX_LIST['tags']).intersection(file_.node.tags.all().values_list('name', flat=True))
    ) or any(substring in file_.node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    if not file_.name or not file_.node.is_public or delete or file_.node.is_deleted or file_.node.archiving or file_node_is_qa:
        client().delete(
            index=index,
            doc_type='file',
            id=file_._id,
            refresh=True,
            ignore=[404]
        )
        return

    # We build URLs manually here so that this function can be
    # run outside of a Flask request context (e.g. in a celery task)
    file_deep_url = '/{node_id}/files/{provider}{path}/'.format(
        node_id=file_.node._id,
        provider=file_.provider,
        path=file_.path,
    )
    node_url = '/{node_id}/'.format(node_id=file_.node._id)

    guid_url = None
    file_guid = file_.get_guid(create=False)
    if file_guid:
        guid_url = '/{file_guid}/'.format(file_guid=file_guid._id)
    file_doc = {
        'id': file_._id,
        'deep_url': file_deep_url,
        'guid_url': guid_url,
        'tags': list(file_.tags.filter(system=False).values_list('name', flat=True)),
        'name': file_.name,
        'category': 'file',
        'node_url': node_url,
        'node_title': file_.node.title,
        'parent_id': file_.node.parent_node._id if file_.node.parent_node else None,
        'is_registration': file_.node.is_registration,
        'is_retracted': file_.node.is_retracted,
        'extra_search_terms': clean_splitters(file_.name),
    }

    client().index(
        index=index,
        doc_type='file',
        body=file_doc,
        id=file_._id,
        refresh=True
    )

@requires_search
def update_institution(institution, index=None):
    index = index or INDEX
    id_ = institution._id
    if institution.is_deleted:
        client().delete(index=index, doc_type='institution', id=id_, refresh=True, ignore=[404])
    else:
        institution_doc = {
            'id': id_,
            'url': '/institutions/{}/'.format(institution._id),
            'logo_path': institution.logo_path,
            'category': 'institution',
            'name': institution.name,
        }

        client().index(index=index, doc_type='institution', body=institution_doc, id=id_, refresh=True)

@requires_search
def update_cgm(cgm, index=None):
    index = index or INDEX
    id_ = cgm._id
    if cgm.guid.deleted:
        client().delete(index=index, doc_type='collectionObject', id=id_, refresh=True, ignore=[404])
    else:
        collection_object_doc = {
            'id': cgm._id,
            'abstract': cgm.guid.referent.get('description', ''),
            'collectedType': cgm.collected_type,
            'contributors': cgm.guid.referent.get('contributors', []),
            'status': cgm.status,
            'subjects': cgm.guid.referent.get('subjects', []),
            'title': cgm.guid.referent.title,
            'url': cgm.guid.referent.get('url'),
        }

        client().index(index=index, doc_type='collectionObject', body=collection_object_doc, id=id_, refresh=True)

@requires_search
def delete_all():
    delete_index(INDEX)


@requires_search
def delete_index(index):
    client().indices.delete(index, ignore=[404])


@requires_search
def create_index(index=None):
    '''Creates index with some specified mappings to begin with,
    all of which are applied to all projects, components, preprints, and registrations.
    '''
    index = index or INDEX
    document_types = ['project', 'component', 'registration', 'user', 'file', 'institution', 'preprint', 'collection_object']
    project_like_types = ['project', 'component', 'registration', 'preprint']
    analyzed_fields = ['title', 'description']

    client().indices.create(index, ignore=[400])  # HTTP 400 if index already exists
    for type_ in document_types:
        mapping = {
            'properties': {
                'tags': NOT_ANALYZED_PROPERTY,
                'license': {
                    'properties': {
                        'id': NOT_ANALYZED_PROPERTY,
                        'name': NOT_ANALYZED_PROPERTY,
                        # Elasticsearch automatically infers mappings from content-type. `year` needs to
                        # be explicitly mapped as a string to allow date ranges, which break on the inferred type
                        'year': {'type': 'string'},
                    }
                }
            }
        }
        if type_ in project_like_types:
            analyzers = {field: ENGLISH_ANALYZER_PROPERTY
                         for field in analyzed_fields}
            mapping['properties'].update(analyzers)

        if type_ == 'user':
            fields = {
                'job': {
                    'type': 'string',
                    'boost': '1',
                },
                'all_jobs': {
                    'type': 'string',
                    'boost': '0.01',
                },
                'school': {
                    'type': 'string',
                    'boost': '1',
                },
                'all_schools': {
                    'type': 'string',
                    'boost': '0.01'
                },
            }
            mapping['properties'].update(fields)
        client().indices.put_mapping(index=index, doc_type=type_, body=mapping, ignore=[400, 404])

@requires_search
def delete_doc(elastic_document_id, node, index=None, category=None):
    index = index or INDEX
    if not category:
        if node.is_registration:
            category = 'registration'
        elif node.is_preprint:
            category = 'preprint'
        else:
            category = node.project_or_component
    client().delete(index=index, doc_type=category, id=elastic_document_id, refresh=True, ignore=[404])


@requires_search
def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
    """Search for contributors to add to a project using elastic search. Request must
    include JSON data with a "query" field.

    :param query: The substring of the username to search for
    :param page: For pagination, the page number to use for results
    :param size: For pagination, the number of results per page
    :param exclude: A list of User objects to exclude from the search
    :param current_user: A User object of the current user

    :return: List of dictionaries, each containing the ID, full name,
        most recent employment and education, profile_image URL of an OSF user

    """
    start = (page * size)
    items = re.split(r'[\s-]+', query)
    exclude = exclude or []
    normalized_items = []
    for item in items:
        try:
            normalized_item = six.u(item)
        except TypeError:
            normalized_item = item
        normalized_item = unicodedata.normalize('NFKD', normalized_item).encode('ascii', 'ignore')
        normalized_items.append(normalized_item)
    items = normalized_items

    query = '  AND '.join('{}*~'.format(re.escape(item)) for item in items) + \
            ''.join(' NOT id:"{}"'.format(excluded._id) for excluded in exclude)

    results = search(build_query(query, start=start, size=size), index=INDEX, doc_type='user')
    docs = results['results']
    pages = math.ceil(results['counts'].get('user', 0) / size)
    validate_page_num(page, pages)

    users = []
    for doc in docs:
        # TODO: use utils.serialize_user
        user = OSFUser.load(doc['id'])

        if current_user and current_user._id == user._id:
            n_projects_in_common = -1
        elif current_user:
            n_projects_in_common = current_user.n_projects_in_common(user)
        else:
            n_projects_in_common = 0

        if user is None:
            logger.error('Could not load user {0}'.format(doc['id']))
            continue
        if user.is_active:  # exclude merged, unregistered, etc.
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
                'social': user.social_links,
                'n_projects_in_common': n_projects_in_common,
                'profile_image_url': profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                                       user,
                                                       use_ssl=True,
                                                       size=settings.PROFILE_IMAGE_MEDIUM),
                'profile_url': user.profile_url,
                'registered': user.is_registered,
                'active': user.is_active
            })

    return {
        'users': users,
        'total': results['counts']['total'],
        'pages': pages,
        'page': page,
    }
