import logging

from website.search import exceptions
from website.search.drivers import base

logger = logging.getLogger(__name__)


class SearchDisabledDriver(base.SearchDriver):

    def __init__(self, warnings=True):
        self._warnings = warnings

    def search(self, query, index=None, doc_type=None, raw=None, refresh=False):
        raise exceptions.SearchDisabledException()

    def search_contributor(self, query, page=0, size=10, exclude=None, current_user=None):
        raise exceptions.SearchDisabledException()

    def _warn_disabled(self, method, *args, **kwargs):
        if self._warnings:
            logger.warning('Search is disabled. Call to `%s(%s, %s)`, ignored', method, args, kwargs)

    def setup(self, types=None):
        self._warn_disabled('setup', types=types)

    def teardown(self, types=None):
        self._warn_disabled('teardown', types=types)

    def index_files(self, **query):
        self._warn_disabled('index_files', query=query)
        return 0

    def index_users(self, **query):
        self._warn_disabled('index_users', query=query)
        return 0

    def index_registrations(self, **query):
        self._warn_disabled('index_registrations', query=query)
        return 0

    def index_projects(self, **query):
        self._warn_disabled('index_projects', query=query)
        return 0

    def index_components(self, **query):
        self._warn_disabled('index_components', query=query)
        return 0

    def index_preprints(self, **query):
        self._warn_disabled('index_preprints', query=query)
        return 0

    def index_collection_submissions(self, **query):
        self._warn_disabled('index_collection_submissions', query=query)
        return 0

    def index_institutions(self, **query):
        self._warn_disabled('index_institutions', query=query)
        return 0

    def remove(self, instance):
        self._warn_disabled('remove', instance=instance)
