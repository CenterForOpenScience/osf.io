
# -*- coding: utf-8 -*-

from __future__ import division

import copy
import functools
import logging
import math
import re
from framework import sentry
import os.path

from django.apps import apps
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from elasticsearch2 import (ConnectionError, Elasticsearch, NotFoundError,
                           RequestError, TransportError, helpers)
from framework.celery_tasks import app as celery_app
from framework.database import paginated
from osf.models import AbstractNode
from osf.models import OSFUser
from osf.models import BaseFileNode
from osf.models import Institution
from osf.models import OSFGroup
from osf.models import QuickFilesNode
from osf.models import Preprint
from osf.models import SpamStatus
from osf.models import Guid
from addons.wiki.models import WikiPage
from osf.models import CollectionSubmission
from osf.models import Comment
from osf.utils.sanitize import unescape_entities
from website import settings
from website.filters import profile_image_url
from osf.models.licenses import serialize_node_license_record
from website.search import exceptions
from website.search.util import (
    build_query, clean_splitters,
    es_escape, convert_query_string,
    unicode_normalize, quote,
    validate_email
)
from website.views import validate_page_num

logger = logging.getLogger(__name__)

USE_NGRAM_FIELD = True

HIGHLIGHT_PRIORITY_DEFAULT_FIELD = '__default'

### kuromoji > ngram
HIGHLIGHT_PRIORITY = ('ngram', HIGHLIGHT_PRIORITY_DEFAULT_FIELD)
### ngram > kuromoji
#HIGHLIGHT_PRIORITY = (HIGHLIGHT_PRIORITY_DEFAULT_FIELD, 'ngram')

# True: use ALIASES_COMMENT
ENABLE_DOC_TYPE_COMMENT = False

# These are the doc_types that exist in the search database
# If changes of ALIASES text happen, please change js_messages.js text as well.
ALIASES_BASE = {
    'project': 'Projects',
    'component': 'Components',
    'registration': 'Registrations',
    'user': 'Users',
    'total': 'All Results',
    'file': 'Files',
    'institution': 'Institutions',
    'preprint': 'Preprints',
    'group': 'Groups',
}

ALIASES_EXT = {
    'wiki': 'Wiki',
}

ALIASES_COMMENT = {
    'comment': 'Comments',
}

ALIASES = {}

DOC_TYPE_TO_MODEL = {
    'component': AbstractNode,
    'project': AbstractNode,
    'registration': AbstractNode,
    'user': OSFUser,
    'file': BaseFileNode,
    'institution': Institution,
    'preprint': Preprint,
    'collectionSubmission': CollectionSubmission,
    'group': OSFGroup
}

# Prevent tokenizing and stop word removal.
NOT_ANALYZED_PROPERTY = {'type': 'string', 'index': 'not_analyzed'}

# Perform stemming on the field it's applied to.
ENGLISH_ANALYZER_PROPERTY = {'type': 'string', 'analyzer': 'english',
                             'term_vector': 'with_positions_offsets'}

# with_positions_offsets: adjust highlighted fields to the middle position.
GRDM_JA_ANALYZER_PROPERTY = {'type': 'string',
                             'analyzer': 'kuromoji_analyzer',
                             'term_vector': 'with_positions_offsets',
                             'fields': {}}
if USE_NGRAM_FIELD:
    GRDM_JA_ANALYZER_PROPERTY['fields'].update({
        'ngram': {
            'type': 'string',
            'analyzer': 'ngram_analyzer',
            'term_vector': 'with_positions_offsets',
        },
    })

def is_japanese_analyzer():
    return settings.SEARCH_ANALYZER == settings.SEARCH_ANALYZER_JAPANESE

def node_includes_wiki():
    return not is_japanese_analyzer()

# INDEX is modified by tests. (TODO: INDEX is unnecessary for GRDM ver.)
INDEX = settings.ELASTIC_INDEX

def es_index_protected(index, private):
    if not index:
        # settings.ELASTIC_INDEX is modified by tests.
        index = settings.ELASTIC_INDEX

    if settings.ENABLE_PRIVATE_SEARCH and private and \
       not index.startswith(settings.ELASTIC_INDEX_PRIVATE_PREFIX):
        # allow only expected implementations to search private projects
        index = settings.ELASTIC_INDEX_PRIVATE_PREFIX + index
    return index

def es_index(index=None):
    return es_index_protected(index, True)

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
            except ConnectionError as e:
                raise exceptions.SearchUnavailableError(str(e))
            except NotFoundError as e:
                raise exceptions.IndexNotFoundError(e.error)
            except RequestError as e:
                logger.error(str(e))
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
def get_aggregations(query, index, doc_type):
    query['aggregations'] = {
        'licenses': {
            'terms': {
                'field': 'license.id'
            }
        }
    }

    res = client().search(index=index, doc_type=doc_type, search_type='count', body=query)
    ret = {
        doc_type: {
            item['key']: item['doc_count']
            for item in agg['buckets']
        }
        for doc_type, agg in res['aggregations'].items()
    }
    ret['total'] = res['hits']['total']
    return ret


@requires_search
def get_counts(count_query, index, clean=True):
    count_query['aggregations'] = {
        'counts': {
            'terms': {
                'field': '_type',
            }
        }
    }

    res = client().search(index=index, doc_type=None, search_type='count', body=count_query)
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


def get_query_string(query):
    if isinstance(query, list):
        if len(query) == 1:  # expect query[0] only
            rv = get_query_string(query[0])
            if rv:
                return rv

    if not isinstance(query, dict):
        return None

    for key, val in query.items():
        if key == 'query' and \
           isinstance(val, str):
            return val  # found
        rv = get_query_string(val)
        if rv:
            return rv
        # next key

    return None


@requires_search
def search(query, index=None, doc_type=None, raw=False, normalize=True, private=False, ext=False):
    """Search for a query

    :param query: The substring of the username/project name/tag to search for
    :param index:
    :param doc_type:
    :param normalize: normalize unicode string
    :param private: allow searching private data
                    (ENABLE_PRIVATE_SEARCH is also required)
    :param ext: include extended doc_types.
                (ENABLE_PRIVATE_SEARCH is also required)

    :return: List of dictionaries, each containing the results, counts, tags and typeAliases
        results: All results returned by the query, that are within the index and search type
        counts: A dictionary in which keys are types and values are counts for that type, e.g, count['total'] is the sum of the other counts
        tags: A list of tags that are returned by the search query
        typeAliases: the doc_types that exist in the search database
    """
    global ALIASES

    ALIASES = copy.deepcopy(ALIASES_BASE)
    if settings.ENABLE_PRIVATE_SEARCH and ext:
        ALIASES.update(ALIASES_EXT)
    if ENABLE_DOC_TYPE_COMMENT:
        ALIASES.update(ALIASES_COMMENT)

    if doc_type is None:
        doc_type = ','.join(ALIASES.keys())
        if raw:
            doc_type += ',collectionSubmission'

    index = es_index_protected(index, private)

    # Quote query string for mutilingual search.
    # This search() is called from ...
    #   - Web Browser  (filtered)
    #   - website.search.util.build_private_search_query
    #   - website.search.util.build_query
    #   - website.search.util.build_query with GUID
    if settings.ENABLE_MULTILINGUAL_SEARCH:
        from_browser = 'filtered' in query['query']
        from_build_private_search_query = 'bool' in query['query'] and \
                                          'must' in query['query']['bool']
        from_build_query = 'query_string' in query['query']
        from_build_query_with_guid = 'bool' in query['query'] and \
                                     'should' in query['query']['bool']
        if from_browser:
            q = query['query']['filtered']['query']['query_string']['query']
            q = convert_query_string(q, normalize=normalize)
            query['query']['filtered']['query']['query_string']['query'] = q
        elif from_build_private_search_query:
            q = query['query']['bool']['must'][0]['query_string']['query']
            q = convert_query_string(q, normalize=normalize)
            query['query']['bool']['must'][0]['query_string']['query'] = q
        elif from_build_query:
            q = query['query']['query_string']['query']
            q = convert_query_string(q, normalize=normalize)
            query['query']['query_string']['query'] = q
        elif from_build_query_with_guid:
            q = query['query']['bool']['should'][0]['query_string']['query']
            q = convert_query_string(q, normalize=normalize)
            query['query']['bool']['should'][0]['query_string']['query'] = q

    tag_query = copy.deepcopy(query)

    for key in ['from', 'size', 'sort', 'highlight']:
        try:
            del tag_query[key]
        except KeyError:
            pass

    aggs_query = copy.deepcopy(tag_query)
    count_query = copy.deepcopy(tag_query)

    tags = get_tags(tag_query, index)
    try:
        del aggs_query['query']['filtered']['filter']
        del count_query['query']['filtered']['filter']
    except KeyError:
        pass
    aggregations = get_aggregations(aggs_query, index, doc_type)
    counts = get_counts(count_query, index)

    # Run the real query and get the results
    raw_results = client().search(index=index, doc_type=doc_type, body=query)

    if raw:
        results = raw_results['hits']['hits']
    else:
        hits = raw_results['hits']['hits']
        hits = merge_highlight(hits)
        hits = set_last_comment(hits)
        results = [hit['_source'] for hit in hits]
        results = format_results(results)

    return_value = {
        'results': results,
        'counts': counts,
        'aggs': aggregations,
        'tags': tags,
        'typeAliases': ALIASES
    }

    return return_value

def highlight_priority_check(a, b):
    if a is None:  # shortcut
        return True
    index_a = -1
    index_b = -1
    if a in HIGHLIGHT_PRIORITY:
        index_a = HIGHLIGHT_PRIORITY.index(a)
    if b in HIGHLIGHT_PRIORITY:
        index_b = HIGHLIGHT_PRIORITY.index(b)
    return index_a > index_b

def merge_highlight(hits):
    for hit in hits:
        highlight = hit.get('highlight', {})
        tmp = {}
        merged_highlight = {}
        for key, value in highlight.items():
            splk = key.split('.')
            lang_field = splk[len(splk) - 1]
            if lang_field in HIGHLIGHT_PRIORITY:
                new_key = '.'.join(splk[:(len(splk) - 1)])
                v = tmp.get(new_key)
                if v:
                    lang_field2 = v[0]
                    # value2 = v[1]   # unused
                    if highlight_priority_check(lang_field, lang_field2):
                        tmp[new_key] = (lang_field, value)
                else:
                    tmp[new_key] = (lang_field, value)
            else:
                tmp[key] = (HIGHLIGHT_PRIORITY_DEFAULT_FIELD, value)
        for key, v in tmp.items():
            merged_highlight[key] = v[1]
        hit['_source']['highlight'] = merged_highlight
    return hits

def set_last_comment(hits):
    for hit in hits:
        s = hit['_source']
        highlight = s['highlight']
        last_comment = None
        last_text = None
        for key, value in highlight.items():
            if not key.startswith('comments.'):
                continue
            try:
                comment_id = int(key.split('.')[1])
            except Exception:
                continue  # unexpected type, ignore
            c = Comment.objects.get(id=comment_id)
            if last_comment is None or c.created > last_comment.created:
                last_comment = c
                last_text = value[0]
        if last_comment is None:
            s['comment'] = None
            continue  # no comment, skip
        d = {}
        d['text'] = last_text
        d['user_id'] = last_comment.user._id
        d['user_name'] = last_comment.user.fullname
        d['date_created'] = last_comment.created.isoformat()
        d['date_modified'] = last_comment.modified.isoformat()
        replyto_user_id = None
        replyto_username = None
        replyto_date_created = None
        replyto_date_modified = None
        replyto = last_comment.target.referent
        if isinstance(replyto, Comment):
            replyto_user_id = replyto.user._id
            replyto_username = replyto.user.fullname
            replyto_date_created = replyto.created.isoformat()
            replyto_date_modified = replyto.modified.isoformat()
        d['replyto_user_id'] = replyto_user_id
        d['replyto_user_name'] = replyto_username
        d['replyto_date_created'] = replyto_date_created
        d['replyto_date_modified'] = replyto_date_modified
        s['comment'] = d
    return hits

def get_file_path(file_id):
    file_node = BaseFileNode.load(file_id)
    if file_node is None:
        return None
    app_config = settings.ADDONS_AVAILABLE_DICT.get(file_node.provider)
    if app_config:
        provider_name = app_config.full_name
    else:
        provider_name = file_node.provider
    return u'{}{}'.format(provider_name, file_node.materialized_path)

def format_results(results):
    ret = []
    for result in results:
        category = result.get('category')
        if category == 'user':
            result['url'] = '/profile/' + result['id']
            # unnormalized
            user = OSFUser.load(result['id'])
            if user:
                job, school = user.get_ongoing_job_school()
                if job is None:
                    job = {}
                result['ongoing_job'] = job.get('institution', '')
                result['ongoing_job_department'] = job.get('department', '')
                result['ongoing_job_title'] = job.get('title', '')
                if school is None:
                    school = {}
                result['ongoing_school'] = school.get('institution', '')
                result['ongoing_school_department'] = school.get('department', '')
                result['ongoing_school_degree'] = school.get('degree', '')
        elif category == 'wiki':
            # get unnormalized names
            wiki = WikiPage.load(result['id'])
            if wiki:
                result['name'] = wiki.page_name
            creator_id, creator_name = user_id_fullname(
                result.get('creator_id'))
            modifier_id, modifier_name = user_id_fullname(
                result.get('modifier_id'))
            result['creator_name'] = creator_name
            result['modifier_name'] = modifier_name
        elif category == 'comment':
            result['page_url'] = '/' + result['page_id'] + '/'
            result['user_url'] = '/profile/' + result['user_id']
            replyto_user_id = result.get('replyto_user_id', None)
            if replyto_user_id:
                result['replyto_user_url'] = '/profile/' + replyto_user_id
            else:
                result['replyto_user_url'] = None
        elif category == 'file':
            file_path = get_file_path(result.get('id'))
            if file_path:
                folder_name = os.path.dirname(file_path)
            else:
                folder_name = None
            result['folder_name'] = folder_name
            parent_info = load_parent(result.get('parent_id'))
            result['parent_url'] = parent_info.get('url') if parent_info else None
            result['parent_title'] = parent_info.get('title') if parent_info else None
            # get unnormalized names
            creator_id, creator_name = user_id_fullname(
                result.get('creator_id'))
            modifier_id, modifier_name = user_id_fullname(
                result.get('modifier_id'))
            result['creator_name'] = creator_name
            result['modifier_name'] = modifier_name
        elif category in {'project', 'component', 'registration'}:
            result = format_result(result, result.get('parent_id'))
        elif category in {'preprint'}:
            result = format_preprint_result(result)
        elif category == 'collectionSubmission':
            continue
        elif not category:
            continue

        ret.append(result)
    return ret


# return (guid, fullname)
def user_id_fullname(guid_id):
    if guid_id:
        user = OSFUser.load(guid_id)
        if user:
            return (guid_id, user.fullname)
    return ('', '')


# for 'project', 'component', 'registration'
def format_result(result, parent_id=None):
    parent_info = load_parent(parent_id)

    # get unnormalized names
    creator_id, creator_name = user_id_fullname(result.get('creator_id'))
    modifier_id, modifier_name = user_id_fullname(result.get('modifier_id'))

    formatted_result = {
        'contributors': result['contributors'],
        'groups': result.get('groups'),
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
        'date_modified': result.get('date_modified'),
        'creator_id': creator_id,
        'creator_name': creator_name,
        'modifier_id': modifier_id,
        'modifier_name': modifier_name,
        'date_registered': result.get('registered_date'),
        'n_wikis': len(result['wikis'] or []),
        'license': result.get('license'),
        'affiliated_institutions': result.get('affiliated_institutions'),
        'highlight': result.get('highlight'),
        'comment': result.get('comment'),
    }

    return formatted_result


def format_preprint_result(result):
    parent_info = None
    formatted_result = {
        'contributors': result['contributors'],
        # TODO: Remove unescape_entities when mako html safe comes in
        'title': unescape_entities(result['title']),
        'url': result['url'],
        'is_component': False,
        'parent_title': None,
        'parent_url': parent_info.get('url') if parent_info is not None else None,
        'tags': result['tags'],
        'is_registration': False,
        'is_retracted': result['is_retracted'],
        'is_pending_retraction': False,
        'embargo_end_date': None,
        'is_pending_embargo': False,
        'description': unescape_entities(result['description']),
        'category': result.get('category'),
        'date_created': result.get('created'),
        'date_registered': None,
        'n_wikis': 0,
        'license': result.get('license'),
        'affiliated_institutions': None,
    }

    return formatted_result


def load_parent(parent_id):
    parent = AbstractNode.load(parent_id)
    if parent and parent.is_public:
        return {
            'title': parent.title,
            'url': parent.url,
            'id': parent._id,
            'is_registation': parent.is_registration,
        }
    return None


COMPONENT_CATEGORIES = set(settings.NODE_CATEGORY_MAP.keys())


def get_doctype_from_node(node):
    if isinstance(node, Preprint):
        return 'preprint'
    if isinstance(node, OSFGroup):
        return 'group'
    if node.is_registration:
        return 'registration'
    elif node.parent_node is None:
        # ElasticSearch categorizes top-level projects differently than children
        return 'project'
    elif node.category in COMPONENT_CATEGORIES:
        return 'component'
    else:
        return node.category

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_node_async(self, node_id, index=None, bulk=False, wiki_page_id=None):
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    if wiki_page_id:
        WikiPage = apps.get_model('addons_wiki.WikiPage')
        wiki_page = WikiPage.load(wiki_page_id)
    else:
        wiki_page = None
    try:
        update_node(node=node, index=index, bulk=bulk, async_update=True, wiki_page=wiki_page)
    except Exception as exc:
        self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_preprint_async(self, preprint_id, index=None, bulk=False):
    Preprint = apps.get_model('osf.Preprint')
    preprint = Preprint.load(preprint_id)
    try:
        update_preprint(preprint=preprint, index=index, bulk=bulk, async_update=True)
    except Exception as exc:
        self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_group_async(self, group_id, index=None, bulk=False, deleted_id=None):
    OSFGroup = apps.get_model('osf.OSFGroup')
    group = OSFGroup.load(group_id)
    try:
        update_group(group=group, index=index, bulk=bulk, async_update=True, deleted_id=deleted_id)
    except Exception as exc:
        self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_comment_async(self, comment_id, index=None, bulk=False):
    Comment = apps.get_model('osf.Comment')
    comment = Comment.load(comment_id)
    try:
        update_comment(comment=comment, index=index, bulk=bulk)
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
    elastic_document = {}
    parent_id = node.parent_id

    normalized_title = unicode_normalize(node.title)

    tags = list(node.tags.filter(system=False).values_list('name', flat=True))
    normalized_tags = [unicode_normalize(tag) for tag in tags]
    latest_log = node.logs.order_by('date').last()
    modifier = latest_log.user

    elastic_document = {
        'id': node._id,
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in node._contributors.all().order_by('contributor___order')
            .values('guids___id')
        ],
        # Bibliographic Contributors (visible=True only) (show in results)
        'contributors': [
            {
                'fullname': x['fullname'],
                'url': '/{}/'.format(x['guids___id']) if x['is_active'] else None,
                'id': x['guids___id']
            }
            for x in node._contributors.filter(contributor__visible=True).order_by('contributor___order')
            .values('fullname', 'guids___id', 'is_active')
        ],
        'groups': [
            {
                'name': x['name'],
                'url': '/{}/'.format(x['_id'])
            }
            for x in node.osf_groups.values('name', '_id')
        ],
        'title': node.title,
        'normalized_title': normalized_title,
        'sort_node_name': node.title,
        'category': category,
        'public': node.is_public,
        'tags': tags,
        'normalized_tags': normalized_tags,
        'description': node.description,
        'normalized_description': unicode_normalize(node.description),
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
        'date_modified': latest_log.date,
        'creator_id': node.creator._id,
        'creator_name': unicode_normalize(node.creator.fullname),
        'modifier_id': modifier._id if modifier else None,
        'modifier_name': unicode_normalize(modifier.fullname) if modifier else None,
        'license': serialize_node_license_record(node.license),
        'affiliated_institutions': list(node.affiliated_institutions.values_list('name', flat=True)),
        'boost': int(not node.is_registration) + 1,  # This is for making registered projects less relevant
        'extra_search_terms': clean_splitters(node.title),
        'comments': comments_to_doc(node._id),
    }
    if node_includes_wiki() and not node.is_retracted:
        wiki_names = []
        for wiki in WikiPage.objects.get_wiki_pages_latest(node):
            # '.' is not allowed in field names in ES2
            wiki_name = unicode_normalize(wiki.wiki_page.page_name.replace('.', ' '))
            elastic_document['wikis'][wiki_name] = unicode_normalize(wiki.raw_text(node))
            wiki_names.append(wiki_name)
        elastic_document['wiki_names'] = wiki_names
    return elastic_document

def comments_to_doc(guid_id):
    comments = {}
    for c in Guid.load(guid_id).comments.iterator():
        if c.is_deleted or c.root_target is None:
            continue
        comments[c.id] = remove_newline(unicode_normalize(c.content))
    return comments

def serialize_preprint(preprint, category):
    elastic_document = {}

    normalized_title = unicode_normalize(preprint.title)
    tags = list(preprint.tags.filter(system=False).values_list('name', flat=True))
    latest_log = preprint.logs.order_by('created').last()
    modifier = latest_log.user
    normalized_tags = [unicode_normalize(tag) for tag in tags]
    elastic_document = {
        'id': preprint._id,
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in preprint._contributors.all().order_by('preprintcontributor___order')
            .values('guids___id')
        ],
        # Bibliographic Contributors (visible=True only)
        'contributors': [
            {
                'fullname': x['fullname'],
                'url': '/{}/'.format(x['guids___id']) if x['is_active'] else None,
                'id': x['guids___id']
            }
            for x in preprint._contributors.filter(preprintcontributor__visible=True).order_by('preprintcontributor___order')
            .values('fullname', 'guids___id', 'is_active')
        ],
        'title': preprint.title,
        'normalized_title': normalized_title,
        'category': category,
        'public': preprint.is_public,
        'published': preprint.verified_publishable,
        'is_retracted': preprint.is_retracted,
        'tags': tags,
        'normalized_tags': normalized_tags,
        'description': preprint.description,
        'normalized_description': unicode_normalize(preprint.description),
        'url': preprint.url,
        'date_created': preprint.created,
        'date_modified': latest_log.created,
        'creator_id': preprint.creator._id,
        'creator_name': unicode_normalize(preprint.creator.fullname),
        'modifier_id': modifier._id if modifier else None,
        'modifier_name': unicode_normalize(modifier.fullname) if modifier else None,
        'license': serialize_node_license_record(preprint.license),
        'boost': 2,  # More relevant than a registration
        'extra_search_terms': clean_splitters(preprint.title),
    }

    return elastic_document

def serialize_wiki(wiki_page, category):
    w = wiki_page
    last_ver = w.get_version()
    first_ver = w.get_version(version=1)

    node = w.node
    elastic_document = {}
    name = w.page_name
    normalized_name = unicode_normalize(name)

    creator = first_ver.user
    if creator:
        creator_id = creator._id
        creator_name = unicode_normalize(creator.fullname)
    else:
        creator_id = ''
        creator_name = ''

    modifier = last_ver.user
    if modifier:
        modifier_id = modifier._id
        modifier_name = unicode_normalize(modifier.fullname)
    else:
        modifier_id = ''
        modifier_name = ''

    elastic_document = {
        'id': w._id,
        'name': normalized_name,
        'sort_wiki_name': name,
        'sort_node_name': node.title,
        'category': category,
        'node_public': node.is_public,
        'date_created': w.created,
        'date_modified': w.modified,
        'creator_id': creator_id,
        'creator_name': creator_name,
        'modifier_id': modifier_id,
        'modifier_name': modifier_name,
        'node_title': node.title,
        'normalized_node_title': unicode_normalize(node.title),
        'node_url': node.url,
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in node._contributors.all().order_by('contributor___order')
            .values('guids___id')
        ],
        'url': w.deep_url,
        'text': unicode_normalize(w.get_version().raw_text(node)),
        'comments': comments_to_doc(w._id),
    }
    return elastic_document

def serialize_group(group, category):
    elastic_document = {}

    normalized_title = unicode_normalize(group.name)
    elastic_document = {
        'id': group._id,
        'members': [
            {
                'fullname': x['fullname'],
                'url': '/{}/'.format(x['guids___id']) if x['is_active'] else None
            }
            for x in group.members_only.values('fullname', 'guids___id', 'is_active')
        ],
        'managers': [
            {
                'fullname': x['fullname'],
                'url': '/{}/'.format(x['guids___id']) if x['is_active'] else None
            }
            for x in group.managers.values('fullname', 'guids___id', 'is_active')
        ],
        'title': group.name,
        'normalized_title': normalized_title,
        'category': category,
        'url': group.url,
        'date_created': group.created,
        'boost': 2,  # More relevant than a registration
        'extra_search_terms': clean_splitters(group.name),
    }

    return elastic_document

def remove_newline(text):
    return text.replace('&#13;&#10;', '')

def serialize_comment(comment, category):
    c = comment
    elastic_document = {}
    page_id = ''  # GUID
    page_name = ''
    if c.page == Comment.FILES:
        guid = c.root_target.referent.get_guid(create=False)
        page_id = guid._id if guid else None
        page_name = c.root_target.referent.name
    elif c.page == Comment.WIKI:
        page_id = c.root_target.referent._id
        page_name = c.root_target.referent.page_name
    else:  # c.page == Comment.OVERVIEW
        page_id = c.node._id
        page_name = c.node.title

    replyto_user_id = ''
    replyto_username = ''
    if isinstance(c.target.referent, Comment):
        replyto_user_id = c.target.referent.user._id
        replyto_username = c.target.referent.user.fullname

    text = remove_newline(unicode_normalize(c.content))

    elastic_document = {
        'id': c._id,
        'page_type': c.page,
        'page_id': page_id,
        'page_name': page_name,
        'normalized_page_name': unicode_normalize(page_name),
        'category': category,
        'node_public': c.node.is_public,
        'date_created': c.created,
        'date_modified': c.modified,
        'user_id': c.user._id,
        'user': c.user.fullname,
        'normalized_user': unicode_normalize(c.user.fullname),
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in c.node._contributors.all().order_by('contributor___order')
            .values('guids___id')
        ],
        'text': text,
        'replyto_user_id': replyto_user_id,
        'replyto_user': replyto_username,
        'normalized_replyto_user': unicode_normalize(replyto_username),
    }
    return elastic_document

@requires_search
def update_comment(comment, index=None, bulk=False):
    index = es_index(index)
    category = 'comment'

    if comment.is_deleted or \
       comment.root_target is None:  # root Node or File is deleted
        delete_comment_doc(comment._id, index=index)
        return None

    elastic_document = serialize_comment(comment, category)
    if bulk:
        return elastic_document
    else:
        client().index(index=index, doc_type=category, id=comment._id, body=elastic_document, refresh=True)

def node_is_ignored(node):
    is_qa_node = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(node.tags.all().values_list('name', flat=True))) or any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    return node.is_deleted \
        or (not settings.ENABLE_PRIVATE_SEARCH and not node.is_public) \
        or node.archiving or node.is_spam \
        or (node.spam_status == SpamStatus.FLAGGED
            and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH) \
        or node.is_quickfiles or is_qa_node

@requires_search
def update_wiki(wiki_page, index=None, bulk=False):
    index = es_index(index)
    category = 'wiki'

    if wiki_page.deleted or node_is_ignored(wiki_page.node):
        delete_wiki_doc(wiki_page._id, index=index)
        return None

    # WikiVersion does not exist just after WikiPage.objects.create()
    if wiki_page.get_version() is None:
        return None

    elastic_document = serialize_wiki(wiki_page, category)
    if bulk:
        return elastic_document
    else:
        client().index(index=index, doc_type=category, id=wiki_page._id, body=elastic_document, refresh=True)

@requires_search
def update_node(node, index=None, bulk=False, async_update=False, wiki_page=None):
    if wiki_page:
        update_wiki(wiki_page, index=index)
        # NOTE: update_node() may be called twice after WikiPage.save()

    from addons.osfstorage.models import OsfStorageFile
    index = es_index(index)
    for file_ in paginated(OsfStorageFile, Q(target_content_type=ContentType.objects.get_for_model(type(node)), target_object_id=node.id)):
        update_file(file_, index=index)

    is_qa_node = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(node.tags.all().values_list('name', flat=True))) or any(substring in node.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    if node.is_deleted or (not settings.ENABLE_PRIVATE_SEARCH and not node.is_public) or node.archiving or node.is_spam or (node.spam_status == SpamStatus.FLAGGED and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH) or node.is_quickfiles or is_qa_node:
        delete_doc(node._id, node, index=index)
        for wiki_page in node.wikis.iterator():
            delete_wiki_doc(wiki_page._id, index=index)
    else:
        category = get_doctype_from_node(node)
        elastic_document = serialize_node(node, category)
        if bulk:
            return elastic_document
        else:
            client().index(index=index, doc_type=category, id=node._id, body=elastic_document, refresh=True)

@requires_search
def update_preprint(preprint, index=None, bulk=False, async_update=False):
    from addons.osfstorage.models import OsfStorageFile
    index = es_index(index)
    for file_ in paginated(OsfStorageFile, Q(target_content_type=ContentType.objects.get_for_model(type(preprint)), target_object_id=preprint.id)):
        update_file(file_, index=index)

    is_qa_preprint = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(preprint.tags.all().values_list('name', flat=True))) or any(substring in preprint.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    if not preprint.verified_publishable or preprint.is_spam or (preprint.spam_status == SpamStatus.FLAGGED and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH) or is_qa_preprint:
        delete_doc(preprint._id, preprint, category='preprint', index=index)
    else:
        category = 'preprint'
        elastic_document = serialize_preprint(preprint, category)
        if bulk:
            return elastic_document
        else:
            client().index(index=index, doc_type=category, id=preprint._id, body=elastic_document, refresh=True)

@requires_search
def update_group(group, index=None, bulk=False, async_update=False, deleted_id=None):
    index = es_index(index)

    if deleted_id:
        delete_group_doc(deleted_id, index=index)
    else:
        category = 'group'
        elastic_document = serialize_group(group, category)
        if bulk:
            return elastic_document
        else:
            client().index(index=index, doc_type=category, id=group._id, body=elastic_document, refresh=True)

def bulk_update_nodes(serialize, nodes, index=None, category=None):
    """Updates the list of input projects

    :param function Node-> dict serialize:
    :param Node[] nodes: Projects, components, registrations, or preprints
    :param str index: Index of the nodes
    :return:
    """
    index = es_index(index)
    actions = []
    for node in nodes:
        serialized = serialize(node)
        if serialized:
            actions.append({
                '_op_type': 'update',
                '_index': index,
                '_id': node._id,
                '_type': category or get_doctype_from_node(node),
                'doc': serialized,
                'doc_as_upsert': True,
            })
    if actions:
        return helpers.bulk(client(), actions)

def bulk_update_wikis(wiki_pages, index=None):
    index = es_index(index)
    category = 'wiki'
    actions = []
    for wiki in wiki_pages:
        serialized = update_wiki(wiki, index=index, bulk=True)
        if serialized:
            actions.append({
                '_op_type': 'update',
                '_index': index,
                '_id': wiki._id,
                '_type': category,
                'doc': serialized,
                'doc_as_upsert': True,
            })
    if actions:
        return helpers.bulk(client(), actions)

def bulk_update_comments(comments, index=None):
    index = es_index(index)
    category = 'comment'
    actions = []
    for comment in comments:
        serialized = update_comment(comment, index=index, bulk=True)
        if serialized:
            actions.append({
                '_op_type': 'update',
                '_index': index,
                '_id': comment._id,
                '_type': category,
                'doc': serialized,
                'doc_as_upsert': True,
            })
    if actions:
        return helpers.bulk(client(), actions)

def serialize_cgm_contributor(contrib):
    return {
        'fullname': contrib['fullname'],
        'url': '/{}/'.format(contrib['guids___id']) if contrib['is_active'] else None
    }

def serialize_cgm(cgm):
    obj = cgm.guid.referent
    tags = list(obj.tags.filter(system=False).values_list('name', flat=True))
    normalized_tags = [unicode_normalize(tag) for tag in tags]

    contributors = []
    if hasattr(obj, '_contributors'):
        contributors = obj._contributors.filter(contributor__visible=True).order_by('contributor___order').values('fullname', 'guids___id', 'is_active')

    return {
        'id': cgm._id,
        'abstract': getattr(obj, 'description', ''),
        'contributors': [serialize_cgm_contributor(contrib) for contrib in contributors],
        'provider': getattr(cgm.collection.provider, '_id', None),
        'modified': max(cgm.modified, obj.modified),
        'collectedType': cgm.collected_type,
        'status': cgm.status,
        'volume': cgm.volume,
        'issue': cgm.issue,
        'programArea': cgm.program_area,
        'subjects': list(cgm.subjects.values_list('text', flat=True)),
        'title': getattr(obj, 'title', ''),
        'url': getattr(obj, 'url', ''),
        'tags': tags,
        'normalized_tags': normalized_tags,
        'category': 'collectionSubmission',
    }

@requires_search
def bulk_update_cgm(cgms, actions=None, op='update', index=None):
    index = es_index(index)
    if not actions and cgms:
        actions = ({
            '_op_type': op,
            '_index': index,
            '_id': cgm._id,
            '_type': 'collectionSubmission',
            'doc': serialize_cgm(cgm),
            'doc_as_upsert': True,
        } for cgm in cgms)

    try:
        helpers.bulk(client(), actions or [], refresh=True, raise_on_error=False)
    except helpers.BulkIndexError as e:
        raise exceptions.BulkUpdateError(e.errors)

def serialize_contributors(node):
    return {
        'contributors': [
            {
                'fullname': x['user__fullname'],
                'url': '/{}/'.format(x['user__guids___id']),
                'id': x['user__guids___id']
            } for x in
            node.contributor_set.filter(visible=True, user__is_active=True).order_by('_order').values('user__fullname', 'user__guids___id')
        ]
    }


bulk_update_contributors = functools.partial(bulk_update_nodes, serialize_contributors)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_contributors_async(self, user_id):
    OSFUser = apps.get_model('osf.OSFUser')
    user = OSFUser.objects.get(id=user_id)
    # If search updated so group member names are displayed on project search results,
    # then update nodes that the user has group membership as well
    p = Paginator(user.visible_contributor_to.order_by('id'), 100)
    for page_num in p.page_range:
        bulk_update_contributors(p.page(page_num).object_list)

@requires_search
def update_user(user, index=None):

    index = es_index(index)
    if not user.is_active:
        try:
            client().delete(index=index, doc_type='user', id=user._id, refresh=True, ignore=[404])
            # update files in their quickfiles node if the user has been marked as spam
            if user.spam_status == SpamStatus.SPAM:
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
            normalized_names[key] = unicode_normalize(val)

    ogjob, ogschool = user.get_ongoing_job_school()
    if ogjob is None:
        ogjob = {}
    ongoing_job = unicode_normalize(ogjob.get('institution', ''))
    ongoing_job_department = unicode_normalize(ogjob.get('department', ''))
    ongoing_job_title = unicode_normalize(ogjob.get('title', ''))
    if ogschool is None:
        ogschool = {}
    ongoing_school = unicode_normalize(ogschool.get('institution', ''))
    ongoing_school_department = unicode_normalize(ogschool.get('department', ''))
    ongoing_school_degree = unicode_normalize(ogschool.get('degree', ''))

    user_doc = {
        'id': user._id,
        'user': user.fullname,
        'sort_user_name': user.fullname,
        'date_created': user.created,
        'date_modified': user.modified,
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
        'user_affiliated_institutions': list(user.affiliated_institutions.values_list('_id', flat=True)),
        'ongoing_job': ongoing_job,
        'ongoing_job_department': ongoing_job_department,
        'ongoing_job_title': ongoing_job_title,
        'ongoing_school': ongoing_school,
        'ongoing_school_department': ongoing_school_department,
        'ongoing_school_degree': ongoing_school_degree,
        'emails': list(user.emails.values_list('address', flat=True))
    }

    client().index(index=index, doc_type='user', body=user_doc, id=user._id, refresh=True)

@requires_search
def update_file(file_, index=None, delete=False):
    index = es_index(index)
    target = file_.target

    # TODO: Can remove 'not file_.name' if we remove all base file nodes with name=None
    file_node_is_qa = bool(
        set(settings.DO_NOT_INDEX_LIST['tags']).intersection(file_.tags.all().values_list('name', flat=True))
    ) or bool(
        set(settings.DO_NOT_INDEX_LIST['tags']).intersection(target.tags.all().values_list('name', flat=True))
    ) or any(substring in target.title for substring in settings.DO_NOT_INDEX_LIST['titles'])
    if not file_.name or (not settings.ENABLE_PRIVATE_SEARCH and not target.is_public) or delete or file_node_is_qa or getattr(target, 'is_deleted', False) or getattr(target, 'archiving', False) or target.is_spam or (
            target.spam_status == SpamStatus.FLAGGED and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH):
        client().delete(
            index=index,
            doc_type='file',
            id=file_._id,
            refresh=True,
            ignore=[404]
        )
        return

    if isinstance(target, Preprint):
        if not getattr(target, 'verified_publishable', False) or target.primary_file != file_ or target.is_spam or (
                target.spam_status == SpamStatus.FLAGGED and settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH):
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
    file_deep_url = '/{target_id}/files/{provider}{path}/'.format(
        target_id=target._id,
        provider=file_.provider,
        path=file_.path,
    )
    if getattr(target, 'is_quickfiles', None):
        node_url = '/{user_id}/quickfiles/'.format(user_id=target.creator._id)
    else:
        node_url = '/{target_id}/'.format(target_id=target._id)

    tags = list(file_.tags.filter(system=False).values_list('name', flat=True))
    normalized_tags = [unicode_normalize(tag) for tag in tags]

    # FileVersion ordering is '-created'. (reversed order)
    first_file = file_.versions.all().last()  # may be None
    last_file = file_.versions.all().first()  # may be None
    if first_file:
        creator = first_file.creator
        creator_id = creator._id
        creator_name = unicode_normalize(creator.fullname)
        date_created = first_file.created
    else:
        creator_id = None
        creator_name = None
        date_created = file_.created
    if last_file:
        modifier = last_file.creator
        modifier_id = modifier._id
        modifier_name = unicode_normalize(modifier.fullname)
        date_modified = last_file.created
    else:
        modifier_id = None
        modifier_name = None
        date_modified = file_.created

    guid_url = None
    file_guid = file_.get_guid(create=False)
    if file_guid:
        guid_url = '/{file_guid}/'.format(file_guid=file_guid._id)
    # File URL's not provided for preprint files, because the File Detail Page will
    # just reroute to preprints detail
    file_doc = {
        'id': file_._id,
        'date_created': date_created,
        'date_modified': date_modified,
        'sort_file_name': file_.name,
        'sort_node_name': getattr(target, 'title', None),
        'creator_id': creator_id,
        'creator_name': creator_name,
        'modifier_id': modifier_id,
        'modifier_name': modifier_name,
        'deep_url': None if isinstance(target, Preprint) else file_deep_url,
        'guid_url': None if isinstance(target, Preprint) else guid_url,
        'tags': tags,
        'normalized_tags': normalized_tags,
        'name': file_.name,
        'normalized_name': unicode_normalize(file_.name),
        'category': 'file',
        'node_url': node_url,
        'node_title': getattr(target, 'title', None),
        'parent_id': target.parent_node._id if getattr(target, 'parent_node', None) else None,
        'is_registration': getattr(target, 'is_registration', False),
        'is_retracted': getattr(target, 'is_retracted', False),
        'extra_search_terms': clean_splitters(file_.name),
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in target._contributors.all().order_by('contributor___order')
            .values('guids___id')
        ],
        'node_public': target.is_public,
        'comments': comments_to_doc(file_guid._id) if file_guid else {}
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
    index = es_index(index)
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
            'sort_institution_name': institution.name,
            'date_created': institution.created,
            'date_modified': institution.modified,
        }

        client().index(index=index, doc_type='institution', body=institution_doc, id=id_, refresh=True)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def update_cgm_async(self, cgm_id, collection_id=None, op='update', index=None):
    CollectionSubmission = apps.get_model('osf.CollectionSubmission')
    if collection_id:
        try:
            cgm = CollectionSubmission.objects.get(
                guid___id=cgm_id,
                collection_id=collection_id,
                collection__provider__isnull=False,
                collection__deleted__isnull=True,
                collection__is_bookmark_collection=False)

        except CollectionSubmission.DoesNotExist:
            logger.exception('Could not find object <_id {}> in a collection <_id {}>'.format(cgm_id, collection_id))
        else:
            if cgm and hasattr(cgm.guid.referent, 'is_public') and cgm.guid.referent.is_public:
                try:
                    update_cgm(cgm, op=op, index=index)
                except Exception as exc:
                    self.retry(exc=exc)
    else:
        cgms = CollectionSubmission.objects.filter(
            guid___id=cgm_id,
            collection__provider__isnull=False,
            collection__deleted__isnull=True,
            collection__is_bookmark_collection=False)

        for cgm in cgms:
            try:
                update_cgm(cgm, op=op, index=index)
            except Exception as exc:
                self.retry(exc=exc)

@requires_search
def update_cgm(cgm, op='update', index=None):
    index = es_index(index)
    if op == 'delete':
        client().delete(index=index, doc_type='collectionSubmission', id=cgm._id, refresh=True, ignore=[404])
        return
    collection_submission_doc = serialize_cgm(cgm)
    client().index(index=index, doc_type='collectionSubmission', body=collection_submission_doc, id=cgm._id, refresh=True)

@requires_search
def delete_all():
    delete_index(es_index())


@requires_search
def delete_index(index):
    client().indices.delete(index, ignore=[404])

PROJECT_LIKE_TYPES = ['project', 'component', 'registration', 'preprint']

@requires_search
def create_index(index=None):
    """Creates index with some specified mappings to begin with,
    all of which are applied to all projects, components, preprints, and registrations.
    """
    index = es_index(index)
    document_types = ['project', 'component', 'registration', 'user', 'file', 'institution', 'preprint', 'collectionSubmission', 'wiki', 'comment']
    project_like_types = PROJECT_LIKE_TYPES
    analyzed_fields = ['title', 'description']  # for project_like_types

    index_settings_ja = {
        'settings': {
            'analysis': {
                'tokenizer': {
                    'kuromoji_tokenizer_search': {
                        'type': 'kuromoji_tokenizer',
                        'mode': 'search',
                        #'user_dictionary': 'dict.txt'
                    },
                    'kuromoji_tokenizer_normal': {
                        'type': 'kuromoji_tokenizer',
                        'mode': 'normal',
                        #'user_dictionary': 'dict.txt'
                    },
                    'ngram_tokenizer': {
                        'type': 'nGram',
                        'min_gram': '2',
                        'max_gram': '3',
                        'token_chars': [
                            'letter',
                            'digit'
                        ]
                    }
                },
                'filter': {
                    'kuromoji_part_of_speech_search': {
                        'type': 'kuromoji_part_of_speech'
                    },
                    'my_synonym': {
                        'type': 'synonym',
                        'synonyms': [
                            'nii,国立情報学研究所',
                        ]
                    }
                },
                # 'char_filter': {
                #     'nfkd_normalizer' : {
                #         'type' : 'icu_normalizer',
                #         'name' : 'nfkc_cf',
                #         'mode' : 'decompose'
                #     }
                # },
                'analyzer': {
                    'kuromoji_analyzer': {
                        'type': 'custom',
                        'char_filter': [
                            'icu_normalizer',
                            'kuromoji_iteration_mark',
                        ],
                        'tokenizer': 'kuromoji_tokenizer_search',
                        'filter': [
                            #'nfkd_normalizer'
                            'lowercase',
                            'kuromoji_baseform',
                            'kuromoji_part_of_speech_search',
                            'ja_stop',
                            #'kuromoji_number', ES6 or later
                            'kuromoji_stemmer',
                            #'my_synonym',
                        ],
                    },
                    'ngram_analyzer': {
                        'type': 'custom',
                        'char_filter': [
                            'html_strip',
                            'icu_normalizer',
                        ],
                        'tokenizer': 'ngram_tokenizer',
                        'filter': [
                            'cjk_width',
                            'lowercase',
                        ],
                    },
                }
            }
        },
        'mappings': {
            '_default_': {
                '_all': {
                    'analyzer': 'kuromoji_analyzer',
                    #'analyzer': 'ngram_analyzer',
                }
            }
        }
    }

    if is_japanese_analyzer():
        analyzer = GRDM_JA_ANALYZER_PROPERTY
        index_settings = index_settings_ja
    else:
        analyzer = ENGLISH_ANALYZER_PROPERTY
        index_settings = None

    client().indices.create(index, body=index_settings,
                            ignore=[400])  # HTTP 400 if index already exists

    for type_ in document_types:
        if type_ == 'collectionSubmission':
            mapping = {
                'properties': {
                    'collectedType': NOT_ANALYZED_PROPERTY,
                    'subjects': NOT_ANALYZED_PROPERTY,
                    'status': NOT_ANALYZED_PROPERTY,
                    'issue': NOT_ANALYZED_PROPERTY,
                    'volume': NOT_ANALYZED_PROPERTY,
                    'programArea': NOT_ANALYZED_PROPERTY,
                    'provider': NOT_ANALYZED_PROPERTY,
                    'title': analyzer,
                    'abstract': analyzer
                }
            }
        else:
            DATE_PROPERTY = {'type': 'date'}
            mapping = {
                'properties': {
                    'date_created': DATE_PROPERTY,
                    'date_modified': DATE_PROPERTY,
                    'sort_node_name': NOT_ANALYZED_PROPERTY,
                    'sort_file_name': NOT_ANALYZED_PROPERTY,
                    'sort_wiki_name': NOT_ANALYZED_PROPERTY,
                    'sort_user_name': NOT_ANALYZED_PROPERTY,
                    'sort_institution_name': NOT_ANALYZED_PROPERTY,
                    'tags': NOT_ANALYZED_PROPERTY,
                    'normalized_tags': NOT_ANALYZED_PROPERTY,
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
                analyzers = {field: analyzer
                             for field in analyzed_fields}
                mapping['properties'].update(analyzers)
                mapping['dynamic_templates'] = [
                    {
                        'comments_fields': {
                            'path_match': 'comments.*',
                            'mapping': analyzer
                        }
                    }, {
                        'wikis_fields': {
                            'path_match': 'wikis.*',
                            'mapping': analyzer
                        }
                    }
                ]

            if type_ == 'user':
                fields = {
                    'user': analyzer,
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
                    'ongoing_job': analyzer,
                    'ongoing_job_department': analyzer,
                    'ongoing_job_title': analyzer,
                    'ongoing_school': analyzer,
                    'ongoing_school_department': analyzer,
                    'ongoing_school_degree': analyzer,
                }
                mapping['properties'].update(fields)
            elif type_ == 'file' or type_ == 'wiki':
                fields = {
                    'name': analyzer,
                    'node_title': analyzer,
                    'text': analyzer,
                }
                mapping['properties'].update(fields)
                mapping['dynamic_templates'] = [
                    {
                        'comments_fields': {
                            'path_match': 'comments.*',
                            'mapping': analyzer
                        }
                    }
                ]
            elif type_ == 'comment':
                fields = {
                    'page_name': analyzer,
                    'text': analyzer,
                }
                mapping['properties'].update(fields)
            elif type_ == 'institution':
                fields = {
                    'name': analyzer,
                }
                mapping['properties'].update(fields)

        client().indices.put_mapping(index=index, doc_type=type_, body=mapping, ignore=[400, 404])

@requires_search
def delete_doc(elastic_document_id, node, index=None, category=None):
    index = es_index(index)
    if not category:
        if isinstance(node, Preprint):
            category = 'preprint'
        elif node.is_registration:
            category = 'registration'
        else:
            category = node.project_or_component
    client().delete(index=index, doc_type=category, id=elastic_document_id, refresh=True, ignore=[404])

@requires_search
def delete_group_doc(deleted_id, index=None):
    index = es_index(index)
    client().delete(index=index, doc_type='group', id=deleted_id, refresh=True, ignore=[404])

@requires_search
def delete_wiki_doc(deleted_id, index=None):
    index = es_index(index)
    client().delete(index=index, doc_type='wiki', id=deleted_id, refresh=True, ignore=[404])

@requires_search
def delete_comment_doc(deleted_id, index=None):
    index = es_index(index)
    client().delete(index=index, doc_type='comment', id=deleted_id, refresh=True, ignore=[404])

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
    escaped_query = es_escape(query)

    start = (page * size)
    items = re.split(r'[\s-]+', query)
    exclude = exclude or []
    normalized_items = []
    for item in items:
        normalized_item = unicode_normalize(item)
        normalized_items.append(normalized_item)
    items = normalized_items

    def item_format_quote(item):
        item, quoted = quote(es_escape(item))
        if quoted:
            return item
        else:
            return u'{}*~'.format(item)

    def item_format_normal(item):
        return u'{}*~'.format(es_escape(item))

    def item_format_japanese_analyzer(item):
        return u'{}'.format(es_escape(item))

    item_format = item_format_normal  # COS ver.
    if is_japanese_analyzer():  # GRDM ver.
        item_format = item_format_japanese_analyzer
    elif settings.ENABLE_MULTILINGUAL_SEARCH:  # old GRDM ver.
        item_format = item_format_quote

    query = u'  AND '.join(item_format(item) for item in items) + \
            ''.join(' NOT id:"{}"'.format(excluded._id) for excluded in exclude)
    if current_user and current_user.affiliated_institutions.all().exists():
        query = query + u' AND user_affiliated_institutions:({})'.format(u' OR '.join(
            u'"{}"'.format(es_escape(inst_id)) for inst_id in
            current_user.affiliated_institutions.values_list('_id', flat=True)
        ))

    match_key = 'emails' if validate_email(escaped_query) else 'id'
    query_object = build_query(query, start=start, size=size, sort=None, match_value=escaped_query, match_key=match_key)
    results = search(query_object, index=None, doc_type='user', normalize=False, private=True)
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
