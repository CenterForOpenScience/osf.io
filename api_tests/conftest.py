from __future__ import print_function

import pytest

from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp
from django.core.management import call_command


@pytest.fixture()
def app():
    return JSONAPITestApp()

# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)

@pytest.fixture(scope='function', autouse=True)
def _es_marker(request, es6_client):
    """Clear out all indices and index templates before and after
    tests marked with ``es``.
    """
    marker = request.node.get_closest_marker('es')
    if marker:

        def teardown_es():
            es6_client.indices.delete(index='*')
            es6_client.indices.delete_template('*')

        teardown_es()
        call_command('sync_metrics')
        yield
        teardown_es()
    else:
        yield
