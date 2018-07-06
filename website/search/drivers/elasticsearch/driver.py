from __future__ import absolute_import
from __future__ import unicode_literals

import math
import re
import copy
import logging

import elasticsearch
from elasticsearch import helpers
from elasticsearch import TransportError

from osf import models
from osf.utils.sanitize import unescape_entities

from website import settings
from website.filters import profile_image_url
from website.search import exceptions
from website.search.drivers import base
from website.search.drivers.elasticsearch import generators
from website.search.util import build_query
from website.views import validate_page_num

logger = logging.getLogger(__name__)
logging.getLogger('urllib3').setLevel(logging.WARN)
logging.getLogger('elasticsearch').setLevel(logging.WARN)
logging.getLogger('elasticsearch.trace').setLevel(logging.WARN)


class ElasticsearchDriver(base.SearchDriver):

    DOC_TYPE = '_doc'

    NODE_LIKE_MAPPINGS = {
        'type': {'index': True, 'type': 'keyword'},
        'category': {'index': True, 'type': 'keyword'},
        'title': {
            'index': True,
            'type': 'text',
            'fields': {
                'en': {
                    'type': 'text',
                    'analyzer': 'english',
                }
            }
        },
        'description': {
            'index': True,
            'type': 'text',
            'fields': {
                'en': {
                    'type': 'text',
                    'analyzer': 'english',
                }
            }
        },
        'tags': {'index': True, 'type': 'keyword', 'normalizer': 'tags'},
        'license': {
            'properties': {
                'id': {'index': True, 'type': 'keyword'},
                'name': {'index': True, 'type': 'keyword'},
                # Copied from elastic_search.py
                # Elasticsearch automatically infers mappings from content-type. `year` needs to
                # be explicitly mapped as a string to allow date ranges, which break on the inferred type
                'year': {'index': True, 'type': 'text'},
            }
        }
    }

    INDICES = {
        'users': {
            'doc_type': 'user',
            'model': models.OSFUser,
            'index_tmpl': '{}-users',
            'action_generator': generators.UserActionGenerator,
            'mappings': {
                'type': {'type': 'keyword'},
                'category': {'index': True, 'type': 'keyword'},
                'job': {'type': 'text', 'boost': 1.0},
                'all_jobs': {'type': 'text', 'boost': 0.01},
                'school': {'type': 'text', 'boost': 1.0},
                'user': {'type': 'text', 'boost': 1.0},
                'all_schools': {'type': 'text', 'boost': 0.01},
            }
        },

        'files': {
            'doc_type': 'file',
            'model': models.BaseFileNode,
            'index_tmpl': '{}-files',
            'action_generator': generators.FileActionGenerator,
            'mappings': {
                'type': {'index': True, 'type': 'keyword'},
                'category': {'index': True, 'type': 'keyword'},
                'title': {'index': True, 'type': 'text', 'analyzer': 'english'},
                'description': {'index': True, 'type': 'text', 'analyzer': 'english'},
                'tags': {'index': True, 'type': 'keyword'},
            }
        },

        'institutions': {
            'doc_type': 'institution',
            'model': models.Institution,
            'index_tmpl': '{}-institutions',
            'action_generator': generators.InstitutionActionGenerator,
            'mappings': {
                'type': {'index': True, 'type': 'keyword'},
                'category': {'index': True, 'type': 'keyword'},
            }
        },

        'projects': {
            'doc_type': 'project',
            'model': models.Node,
            'index_tmpl': '{}-nodes-projects',
            'action_generator': generators.ProjectActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'components': {
            'doc_type': 'component',
            'model': models.Node,
            'index_tmpl': '{}-nodes-components',
            'action_generator': generators.ComponentActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'preprints': {
            'doc_type': 'preprint',
            'model': models.PreprintService,
            'index_tmpl': '{}-nodes-preprints',
            'action_generator': generators.PreprintActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'registrations': {
            'doc_type': 'registration',
            'model': models.Registration,
            'index_tmpl': '{}-nodes-registrations',
            'action_generator': generators.RegistrationActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'collection_submissions': {
            'doc_type': 'collectionSubmission',
            'model': models.CollectedGuidMetadata,
            'index_tmpl': '{}-collection-submissions',
            'action_generator': generators.CollectionSubmission,
            'mappings': {
                'type': {'index': True, 'type': 'keyword'},
                'category': {'index': True, 'type': 'keyword'},
            }
        },
    }

    def __init__(self, urls, index_prefix, warnings=True, refresh=False, **kwargs):
        super(ElasticsearchDriver, self).__init__(warnings=warnings)
        self._refresh = refresh
        self._index_prefix = index_prefix
        self._client = elasticsearch.Elasticsearch(urls, **kwargs)

    def setup(self, types=None):
        for type_, config in self.INDICES.items():
            if types is not None and type_ not in types:
                continue
            self._client.indices.create(
                index=config['index_tmpl'].format(self._index_prefix),
                body={
                    'settings': {
                        # TODO
                        'index.number_of_shards': 1,
                        'index.number_of_replicas': 0,
                        # 'index.shard.check_on_startup': False,
                        # 'index.refresh_interval': -1,
                        # 'index.gc_deletes': 0,
                        # 'index.translog.sync_interval': '1s',
                        # 'index.translog.durability': 'async',
                        'analysis': {
                            'normalizer': {
                                'tags': {
                                    'type': 'custom',
                                    'char_filter': [],
                                    'filter': ['lowercase', 'preserve_asciifolding']
                                }
                            },
                            'analyzer': {
                                'default': {
                                    'type': 'standard',
                                    # 'tokenizer': 'standard',
                                    'filter': ['standard', 'preserve_asciifolding', 'lowercase'],
                                }
                            },
                            'filter': {
                                'preserve_asciifolding': {
                                    'type': 'asciifolding',
                                    'preserve_original': True,
                                }
                            }
                        }
                    },
                    'mappings': {self.DOC_TYPE: {'properties': config['mappings']}},
                    'aliases': {
                        # TODO
                    },
                },
                ignore=[400]
            )

    def _before_migrate(self, types):
        for type_, config in self.INDICES.items():
            if type_ not in types:
                continue
            self._client.indices.put_settings(
                index=config['index_tmpl'].format(self._index_prefix),
                body={
                    'index.refresh_interval': '10s'
                },
            )

    def _after_migrate(self, types):
        for type_, config in self.INDICES.items():
            if type_ not in types:
                continue
            self._client.indices.put_settings(
                index=config['index_tmpl'].format(self._index_prefix),
                body={
                    'index.refresh_interval': '1s'
                },
            )

    def teardown(self, types=None):
        types = types or self.INDEXABLE_TYPES
        for type_, config in self.INDICES.items():
            if type_ not in types:
                continue
            self._client.indices.delete(index=config['index_tmpl'].format(self._index_prefix), ignore=[404])

    def _do_index(self, type_, query):
        x, action_generator = 0, self.INDICES[type_]['action_generator'](
            self.INDICES[type_]['index_tmpl'].format(self._index_prefix),
            self.DOC_TYPE,
            initial_query=query,
        )

        import time

        start = time.time()
        for ok, response in helpers.streaming_bulk(self._client, action_generator, raise_on_error=False):
            if not ok and response.values()[0]['status'] != 404:
                raise exceptions.SearchException('Failed to index document {}'.format(response))
            # abusing that bool -> int so that documents that fail to get deleted
            # don't add to the total count
            x += int(ok)
            if x > 0 and x % 1000 == 0:
                print(x)
        print('{!r}: {} IN {}'.format(action_generator, x, time.time() - start))
        return x

    def index_files(self, **query):
        return self._do_index('files', query)

    def index_users(self, **query):
        return self._do_index('users', query)

    def index_institutions(self, **query):
        return self._do_index('institutions', query)

    def index_registrations(self, **query):
        return self._do_index('registrations', query)

    def index_projects(self, **query):
        return self._do_index('projects', query)

    def index_components(self, **query):
        return self._do_index('components', query)

    def index_preprints(self, **query):
        return self._do_index('preprints', query)

    def index_collection_submissions(self, **query):
        return self._do_index('collection_submissions', query)

    def remove(self, instance):
        for config in self.INDICES.values():
            # Don't break out of this loop to handle special cases.
            # Namely projects/components
            if isinstance(instance, config['model']):
                self._client.delete(
                    ignore=[404],
                    doc_type=self.DOC_TYPE,
                    id=instance._id,
                    index=config['index_tmpl'].format(self._index_prefix)
                )

    # NOTE: the following implementations where more or less copypasta'd from elastic_search.py
    # Too much special functionality to tackle just yet

    def _get_aggregations(self, query, indices):
        query['aggregations'] = {
            'licenses': {
                'terms': {
                    'field': 'license.id'
                }
            },
            'counts': {
                'terms': {'field': 'type'}
            },
            'tag_cloud': {
                'terms': {'field': 'tags'}
            }
        }

        # TODO indexes/types
        res = self._client.search(
            size=0,
            body=query,
            index=indices,
        )

        ret = {}
        ret['licenses'] = {
            item['key']: item['doc_count']
            for item in res['aggregations']['licenses']['buckets']
        }
        ret['total'] = res['hits']['total']

        ret['counts'] = {
            x['key']: x['doc_count']
            for x in res['aggregations']['counts']['buckets']
            if x['key'] in self.ALIASES.keys()
        }
        ret['counts']['total'] = sum(ret['counts'].values())

        ret['tags'] = res['aggregations']['tag_cloud']['buckets']

        return ret

        # ret = {
        #     doc_type: {
        #         item['key']: item['doc_count']
        #         for item in agg['buckets']
        #     } for doc_type, agg in res['aggregations'].iteritems()
        # }
        # ret['total'] = res['hits']['total']

        # return ret

    # def _get_counts(self, query, clean=True):
    #     query['aggregations'] = {
    #         'counts': {
    #             'terms': {'field': 'type'}
    #         }
    #     }

    #     res = self._client.search(
    #         size=0,
    #         body=query,
    #         index=self._index_prefix + '*',
    #     )

    #     counts = {
    #         x['key']: x['doc_count']
    #         for x in res['aggregations']['counts']['buckets']
    #         if x['key'] in self.ALIASES.keys()
    #     }

    #     counts['total'] = sum([val for val in counts.values()])
    #     return counts

    # def _get_tags(self, query, indices):
    #     query['aggregations'] = {
    #         'tag_cloud': {
    #             'terms': {'field': 'tags'}
    #         }
    #     }

    #     results = self._client.search(index=indices, body=query)
    #     tags = results['aggregations']['tag_cloud']['buckets']

    #     return tags

    def load_parent(self, parent_id):
        parent = models.AbstractNode.load(parent_id)
        if parent and parent.is_public:
            return {
                'title': parent.title,
                'url': parent.url,
                'id': parent._id,
                'is_registation': parent.is_registration,
            }
        return None

    def format_results(self, results):
        ret = []
        for result in results:
            if result.get('category') == 'user':
                result['url'] = '/profile/' + result['id']
            elif result.get('category') == 'file':
                parent_info = self.load_parent(result.get('parent_id'))
                result['parent_url'] = parent_info.get('url') if parent_info else None
                result['parent_title'] = parent_info.get('title') if parent_info else None
            elif result.get('category') in {'project', 'component', 'registration', 'preprint'}:
                result = self.format_result(result, result.get('parent_id'))
            elif result.get('category') == 'collectionSubmission':
                continue
            elif not result.get('category'):
                continue

            ret.append(result)
        return ret

    def format_result(self, result, parent_id=None):
        parent_info = self.load_parent(parent_id)
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

    def _doc_type_to_indices(self, doc_type):
        if not doc_type:
            return self._index_prefix + '*'
        for value in self.INDICES.values():
            if value['doc_type'] == doc_type:
                return value['index_tmpl'].format(self._index_prefix)
        raise NotImplementedError(doc_type)

    def search(self, query, doc_type=None, raw=False, refresh=False):
        if refresh or self._refresh:
            self._client.indices.refresh(self._doc_type_to_indices(doc_type))

        aggs_query = copy.deepcopy(query)

        indices = self._doc_type_to_indices(doc_type)

        for key in ['from', 'size', 'sort']:
            aggs_query.pop(key, None)

        try:
            del aggs_query['query']['filtered']['filter']
        except KeyError:
            pass

        try:
            aggregations = self._get_aggregations(aggs_query, indices)

            # Run the real query and get the results
            raw_results = self._client.search(index=indices, doc_type=self.DOC_TYPE, body=query)
        except TransportError as e:
            if e.info['error']['failed_shards'][0]['reason']['reason'].startswith('Failed to parse'):
                raise exceptions.MalformedQueryError(e.info['error']['failed_shards'][0]['reason']['reason'])
            raise exceptions.SearchException(e.info)

        results = [hit['_source'] for hit in raw_results['hits']['hits']]

        return {
            'aggs': {
                'total': aggregations['total'],
                'licenses': aggregations['licenses'],
            },
            'typeAliases': self.ALIASES,
            'tags': aggregations['tags'],
            'counts': aggregations['counts'],
            'results': raw_results['hits']['hits'] if raw else self.format_results(results),
        }

    def search_contributor(self, query, page=0, size=10, exclude=None, current_user=None, refresh=False):
        start = (page * size)
        items = re.split(r'[\s-]+', query)
        exclude = exclude or []

        query = '  AND '.join('{}*~'.format(re.escape(item)) for item in items)
        query += ''.join(' NOT id:"{}"'.format(excluded._id) for excluded in exclude)

        results = self.search(build_query(query, start=start, size=size), doc_type='user', refresh=refresh)
        docs = results['results']
        pages = math.ceil(results['counts'].get('user', 0) / size)
        validate_page_num(page, pages)

        users = []
        for doc in docs:
            # TODO: use utils.serialize_user
            user = models.OSFUser.load(doc['id'])

            if current_user and current_user._id == user._id:
                n_projects_in_common = -1
            elif current_user:
                n_projects_in_common = current_user.n_projects_in_common(user)
            else:
                n_projects_in_common = 0

            if user is None:
                logger.error('Could not load user {0}'.format(doc['id']))
                continue

            if not user.is_active:
                continue

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
                'profile_image_url': profile_image_url(
                    settings.PROFILE_IMAGE_PROVIDER,
                    user,
                    use_ssl=True,
                    size=settings.PROFILE_IMAGE_MEDIUM
                ),
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
