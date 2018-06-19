import logging

from website.search import exceptions
from website.search.drivers import base

logger = logging.getLogger(__name__)


class SearchDisabledDriver(base.SearchDriver):

    @property
    def migrator(self):
        return SearchDisabledMigrator(self)

    def __init__(self, warnings=True):
        self._warnings = warnings

    def search(query, index=None, doc_type=None, raw=None):
        raise exceptions.SearchDisabledException()

    def search_contributor(self, query, page=0, size=10, exclude=None, current_user=None):
        raise exceptions.SearchDisabledException()

    def _warn_disabled(self, method, *args, **kwargs):
        if self._warnings:
            logger.warning('Search is disabled. Call to `%s(%s, %s)`, ignored', method, args, kwargs)

    def update_node(self, node, index=None, bulk=False, async=True, saved_fields=None):
        self._warn_disabled('update_node', node)

    def bulk_update_nodes(self, serialize, nodes, index=None):
        self._warn_disabled('bulk_update_nodes', serialize, nodes)

    def delete_node(self, node, index=None):
        self._warn_disabled('delete_node', node, index=index)

    def update_contributors_async(self, user_id):
        self._warn_disabled('update_contributors_async', user_id)

    def update_user(self, user, index=None, async=True):
        self._warn_disabled('update_user', user, index=index)

    def update_file(self, file_, index=None, delete=False):
        self._warn_disabled('update_file', file_, delete=delete)

    def update_institution(self, institution, index=None):
        self._warn_disabled('update_institution', institution)

    def delete_all(self):
        self._warn_disabled('delete_all')

    def delete_index(self):
        self._warn_disabled('delete_index')

    def create_index(self, index=None):
        self._warn_disabled('create_index', index=index)


class SearchDisabledMigrator(base.SearchMigrator):

    def setup(self):
        self._driver._warn_disabled('migrator.setup')

    def teardown(self):
        self._driver._warn_disabled('migrator.teardown')
