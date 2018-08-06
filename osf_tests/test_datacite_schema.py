import pytest
from datacite import schema40

from osf_tests.factories import ProjectFactory
from addons.osfstorage.models import OsfStorageFile


@pytest.fixture()
def node():
    return ProjectFactory()


@pytest.fixture()
def file_node(node):
    filename = 'test file'
    file_node = OsfStorageFile.create(
        node=node,
        path='/{}'.format(filename),
        name=filename,
        materialized_path='/{}'.format(filename))
    file_node.save()
    return file_node


@pytest.fixture()
def descriptions():
    return {
        'descriptions': [{
            'description': 'Hi I\'m a abstract',
            'descriptionType': 'Abstract'
        }, {
            'description': 'Hi I\'m technical info',
            'descriptionType': 'TechnicalInfo'
        }]
    }


@pytest.fixture()
def funding_references():
    return {
        'fundingReferences': [{
            'funderName': 'Laura and John Arnold Foundation',
            'funderIdentifier': {
                'funderIdentifier': '<Crossref Funder ID> or whatever',
                'funderIdentifierType': 'Crossref Funder ID',
            },
            'awardTitle': 'Reproducibility Project: Cancer Biology'
        }]
    }


@pytest.fixture()
def resource_type():
    return {
        'resourceType': {
            'resourceType': 'something user specified',
            'resourceTypeGeneral': 'Image'
        }
    }


@pytest.fixture()
def related_identifiers():
    return {
        'relatedIdentifiers': [{
            'relatedIdentifier': 'something user specified',
            'relatedIdentifierType': 'DOI',
            'relationType': 'IsCitedBy'
        }]
    }


@pytest.fixture()
def misc_metadata():
    # These requires little validation so they will be lumped together.
    return {
        'language': 'something user specified',
        'sizes': ['something', 'user', 'specified'],
        'formats': ['something', 'user', 'specified'],
    }


@pytest.mark.django_db
class TestDataciteSchema:

    def test_entire_datacite_schema_valid(self, file_node, descriptions, funding_references, related_identifiers, misc_metadata):
        # Assert that the user created json syncs with automatically generated json to validate properly.

        schema = file_node.datacite_metadata
        assert schema40.validate(schema)

        schema.update(descriptions)
        assert schema40.validate(schema)

        schema.update(funding_references)
        assert schema40.validate(schema)

        schema.update(related_identifiers)
        assert schema40.validate(schema)

        schema.update(misc_metadata)
        assert schema40.validate(schema)
