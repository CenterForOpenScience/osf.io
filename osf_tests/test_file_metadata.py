import pytest
from addons.osfstorage.models import OsfStorageFile
from osf_tests.factories import ProjectFactory
from website.settings import DOI_FORMAT, DATACITE_PREFIX
from datacite import schema40
from jsonschema import ValidationError


@pytest.fixture()
def node():
    return ProjectFactory()

@pytest.fixture()
def file_node(node):
    filename = 'test file'
    file_node = OsfStorageFile.create(
        target=node,
        path='/{}'.format(filename),
        name=filename,
        materialized_path='/{}'.format(filename))
    return file_node

@pytest.mark.django_db
class TestFileMetadata:

    def test_record_created_post_save(self, node, file_node):
        file_node.save()
        assert file_node.records.all().count() == 1

        record = file_node.records.first()
        assert record.schema.name == 'datacite'
        assert record.file == file_node

    def test_serialize_record(self, node, file_node):
        file_node.save()
        assert file_node.records.all().count() == 1

        record = file_node.records.first()
        assert record.serialize()['identifier']['identifier'] == DOI_FORMAT.format(prefix=DATACITE_PREFIX, guid=node._id)
        assert schema40.validate(record.serialize())

    def test_validate_record(self, node, file_node):
        file_node.save()
        assert file_node.records.all().count() == 1

        record = file_node.records.first()
        json_data = record.serialize()
        assert record.validate(json_data) is None

        del json_data['identifier']
        with pytest.raises(ValidationError) as exc:
            assert record.validate(json_data)

        assert exc.value.message == "u'identifier' is a required property"
