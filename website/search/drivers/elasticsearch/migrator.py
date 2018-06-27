from __future__ import absolute_import

import logging

from elasticsearch import helpers

from website.search.drivers import base
from website.search.drivers.elasticsearch import generators


logging.getLogger('urllib3').setLevel(logging.WARN)
logging.getLogger('elasticsearch').setLevel(logging.WARN)
logging.getLogger('elasticsearch.trace').setLevel(logging.WARN)


class ElasticsearchMigrator(base.SearchMigrator):

    NODE_LIKE_MAPPINGS = {
        'title': {'index': True, 'type': 'text', 'analyzer': 'english'},
        'description': {'index': True, 'type': 'text', 'analyzer': 'english'},
        'tags': {'index': True, 'type': 'keyword'},
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
        'user': {
            'index_tmpl': '{}-users',
            'action_generator': generators.UserActionGenerator,
            'mappings': {
                'job': {'type': 'text', 'boost': 1.0},
                'all_jobs': {'type': 'text', 'boost': 0.01},
                'school': {'type': 'text', 'boost': 1.0},
                'all_schools': {'type': 'text', 'boost': 0.01},
            }
        },

        'file': {
            'index_tmpl': '{}-files',
            'action_generator': generators.FileActionGenerator,
            'mappings': {
                'title': {'index': True, 'type': 'text', 'analyzer': 'english'},
                'description': {'index': True, 'type': 'text', 'analyzer': 'english'},
                'tags': {'index': True, 'type': 'keyword'},
            }
        },

        'institution': {
            'index_tmpl': '{}-institutions',
            'action_generator': generators.InstitutionActionGenerator,
            'mappings': {}
        },

        'project': {
            'index_tmpl': '{}-nodes-projects',
            'action_generator': generators.ProjectActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'component': {
            'index_tmpl': '{}-nodes-components',
            'action_generator': generators.ComponentActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'preprint': {
            'index_tmpl': '{}-nodes-preprints',
            'action_generator': generators.PreprintActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'registration': {
            'index_tmpl': '{}-nodes-registrations',
            'action_generator': generators.RegistrationActionGenerator,
            'mappings': NODE_LIKE_MAPPINGS,
        },

        'node_collection_submission': {
            'index_tmpl': '{}-collection-submissions',
            'action_generator': generators.NodeCollectionSubmition,
            'mappings': {}
        },
    }

    @property
    def _client(self):
        return self._driver._client

    @property
    def _index(self):
        return self._driver._index

    def _before_migrate(self):
        for type_, config in self.INDICES.items():
            self._client.indices.put_settings(
                index=config['index_tmpl'].format(self._index),
                body={
                    'index.refresh_interval': '10s'
                },
            )

    def _after_migrate(self):
        for type_, config in self.INDICES.items():
            self._client.indices.put_settings(
                index=config['index_tmpl'].format(self._index),
                body={
                    'index.refresh_interval': '1s'
                },
            )

    def setup(self):
        for type_, config in self.INDICES.items():
            self._client.indices.create(
                index=config['index_tmpl'].format(self._index),
                body={
                    'settings': {
                        # TODO
                    },
                    'mappings': {'doc': {'properties': config['mappings']}},
                    'aliases': {
                        # TODO
                    },
                },
                ignore=[400]
            )

    def teardown(self):
        for config in self.INDICES.values():
            self._client.indices.delete(index=config['index_tmpl'].format(self._index), ignore=[404])

    def migrate_projects(self):
        return self._do_migrate('project')

    def migrate_components(self):
        return self._do_migrate('component')

    def migrate_registrations(self):
        return self._do_migrate('registration')

    def migrate_preprints(self):
        return self._do_migrate('preprint')

    def migrate_files(self):
        return self._do_migrate('file')

    def migrate_institutions(self):
        return self._do_migrate('institution')

    def migrate_users(self):
        return self._do_migrate('user')

    def migrate_collection_submissions(self):
        return self._do_migrate('node_collection_submission')

    def _do_migrate(self, type_):
        x, action_generator = 0, self.INDICES[type_]['action_generator'](
            self.INDICES[type_]['index_tmpl'].format(self._index),
            'doc'
        )

        for ok, response in helpers.streaming_bulk(self._client, action_generator):
            x += 1
            if x % 1000 == 0:
                print(x)
        print('DID {} {} DOCUMENTS'.format(x, type_))
