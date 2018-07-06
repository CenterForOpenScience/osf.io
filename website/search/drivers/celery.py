import logging

from framework.celery_tasks import app

from website.search.drivers import base
from framework.celery_tasks.handlers import enqueue_task

logger = logging.getLogger(__name__)


@app.task(ignore_results=True)
def _celery_search_task(method, *args, **kwargs):
    from website.search import driver
    if not isinstance(driver._get_current_object(), CelerySearchDelegator):
        raise TypeError('Recieved a SearchDriver that is not CelerySearchDelegator in _celery_search_task')
    return getattr(driver._inner, method)(*args, **kwargs)


class CelerySearchDelegator(base.SearchDriver):

    def __init__(self, warnings=False):
        super(CelerySearchDelegator, self).__init__(self, warnings=warnings)

    def setup(self, *args, **kwargs):
        return self._inner.setup(*args, **kwargs)

    def teardown(self, *args, **kwargs):
        return self._inner.teardown(*args, **kwargs)

    def search(self, *args, **kwargs):
        return self._inner.search(*args, **kwargs)

    def search_contributor(self, *args, **kwargs):
        return self._inner.search_contributor(*args, **kwargs)

    def _dispatch(self, method, *args, **kwargs):
        return enqueue_task(_celery_search_task.s(method, *args, **kwargs))

    def index_users(self, **query):
        return self._dispatch('index_users', query=query)

    def index_registrations(self, **query):
        return self._dispatch('index_registrations', query=query)

    def index_projects(self, **query):
        return self._dispatch('index_projects', query=query)

    def index_components(self, **query):
        return self._dispatch('index_components', query=query)

    def index_preprints(self, **query):
        return self._dispatch('index_preprints', query=query)

    def index_collection_submissions(self, **query):
        return self._dispatch('index_collection_submissions', query=query)

    def index_institutions(self, **query):
        return self._dispatch('index_institutions', query=query)
