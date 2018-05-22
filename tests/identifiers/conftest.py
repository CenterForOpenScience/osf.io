import os
import pytest

from osf.models import NodeLicense
from website.app import init_app
from framework.flask import rm_handlers
from framework.django.handlers import handlers as django_handlers

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, 'fixtures')


@pytest.fixture(autouse=True, scope='session')
def app():
    try:
        test_app = init_app(routes=True, set_backends=False)
    except AssertionError:  # Routes have already been set up
        test_app = init_app(routes=False, set_backends=False)

    rm_handlers(test_app, django_handlers)

    test_app.testing = True
    return test_app

@pytest.fixture()
def datacite_node_metadata():
    with open(os.path.join(FIXTURES, 'datacite_node_metadata.xml'), 'r') as fp:
        return fp.read()

@pytest.fixture()
def datacite_metadata_response():
    with open(os.path.join(FIXTURES, 'datacite_post_metadata_response.xml'), 'r') as fp:
        return fp.read()


@pytest.fixture()
def crossref_preprint_metadata():
    with open(os.path.join(FIXTURES, 'crossref_preprint_metadata.xml'), 'r') as fp:
        return fp.read()

@pytest.fixture()
def crossref_success_response():
    return """
        \n\n\n\n<html>\n<head><title>SUCCESS</title>\n</head>\n<body>\n<h2>SUCCESS</h2>\n<p>
        Your batch submission was successfully received.</p>\n</body>\n</html>\n
        """
