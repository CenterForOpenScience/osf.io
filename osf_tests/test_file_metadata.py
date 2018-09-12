import pytest
from datacite import schema40
import jsonschema

from osf.models import FileMetadataSchema
from addons.osfstorage.models import OsfStorageFile
from addons.osfstorage.tests.factories import FileVersionFactory
from osf_tests.factories import ProjectFactory


@pytest.fixture()
def node():
    return ProjectFactory()

@pytest.fixture()
def file_node(node):
    filename = 'test file'
    osf_file = OsfStorageFile.objects.create(
        target=node,
        path='/{}'.format(filename),
        name=filename,
        materialized_path='/{}'.format(filename)
    )
    version = FileVersionFactory()
    osf_file.versions.add(version)
    osf_file.save()

    return osf_file

@pytest.mark.django_db
class TestFileMetadata:

    def test_record_created_post_save(self, node, file_node):
        # check there's a record for every FileMetadataSchema
        assert FileMetadataSchema.objects.count() > 0
        assert file_node.records.count() == FileMetadataSchema.objects.count()

        for record in file_node.records.all().select_related('file'):
            assert record.file == file_node

    def test_serialize_record_datacite(self, node, file_node):
        record = file_node.records.get(schema___id='datacite')
        serialized_record = record.serialize()

        # test DOI
        doi = node.get_identifier('doi').value
        assert serialized_record['identifier']['identifier'] == doi
        assert schema40.validate(serialized_record)

        # no resource type provided
        assert serialized_record['resourceType']['resourceType'] == '(:unas)'
        assert serialized_record['resourceType']['resourceTypeGeneral'] == 'Other'

        # Add external DOI with external_doi_for_file

        # test most recent version
        most_recent_version = file_node.versions.all().order_by('-created').first()
        assert serialized_record['version'] == most_recent_version.identifier

    def test_validate_record(self, node, file_node):
        # valid data with no identifier
        record = file_node.records.first()
        json_data = record.serialize()
        assert record.validate(json_data) is None

        # make sure another validation error raises
        del json_data['titles']
        with pytest.raises(jsonschema.ValidationError) as exc:
            assert record.validate(json_data)
        assert 'titles' in exc.value.message

    def test_update_record(self, node, file_node):
        # manually set record.metadata
        initial_metadata = {
            'file_description': 'Hello this is a description',
            'resource_type': 'Book'
        }
        record = file_node.records.first()
        record.metadata = initial_metadata
        record.save()
        new_metadata = {
            'funding_agency': 'Woop',
            'publication_year': '2010'
        }
        # Update record.metadata using serializer method
        record.serializer.update(record, new_metadata)

        assert initial_metadata.keys() not in record.metadata.keys()

        # Test using incorrect values once user jsonschema is in place
