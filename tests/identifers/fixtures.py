import pytest

from osf_tests.factories import (
    RegistrationFactory,
    PreprintFactory,
    PreprintProviderFactory,
    AuthUserFactory
)

from osf.models import NodeLicense
from website.identifiers.clients import DataCiteClient, CrossRefClient


@pytest.fixture()
def datacite_client():
    return DataCiteClient()


@pytest.fixture()
def crossref_client():
    return CrossRefClient()


@pytest.fixture()
def registration():
    return RegistrationFactory()


@pytest.fixture
def datacite_node_metadata():
    with open('tests/identifers/fixtures/datacite_node_metadata.xml', 'r') as fp:
        return fp.read()


@pytest.fixture
def datacite_metadata_response():
    with open('tests/identifers/fixtures/datacite_post_metadata_response.xml', 'r') as fp:
        return fp.read()


@pytest.fixture
def crossref_preprint_metadata():
    with open('tests/identifers/fixtures/crossref_preprint_metadata.xml', 'r') as fp:
        return fp.read()


@pytest.fixture()
def preprint():
    node_license = NodeLicense.objects.get(name="CC-By Attribution 4.0 International")
    user = AuthUserFactory()
    provider = PreprintProviderFactory()
    node = RegistrationFactory(creator=user, preprint_article_doi='10.31219/FK2osf.io/test!')
    license_details = {
        'id': node_license.license_id,
        'year': '2017',
        'copyrightHolders': ['Jeff Hardy', 'Matt Hardy']
    }
    preprint = PreprintFactory(provider=provider,
                           project=node,
                           is_published=True,
                           license_details=license_details)
    preprint.license.node_license.url = 'https://creativecommons.org/licenses/by/4.0/legalcode'
    return preprint

@pytest.fixture()
def crossref_success_response():
    return """
        \n\n\n\n<html>\n<head><title>SUCCESS</title>\n</head>\n<body>\n<h2>SUCCESS</h2>\n<p>
        Your batch submission was successfully received.</p>\n</body>\n</html>\n
        """


