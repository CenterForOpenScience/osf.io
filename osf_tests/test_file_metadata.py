import json
import pytest
import jsonschema
from django.contrib.contenttypes.models import ContentType

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from website.project.licenses import set_license
from osf.models import FileMetadataSchema, NodeLicense, Guid, NodeLog
from osf_tests.factories import ProjectFactory, SubjectFactory, AuthUserFactory
from api_tests.utils import create_test_file


@pytest.fixture()
def node():
    return ProjectFactory()

@pytest.fixture()
def osf_file(node):
    return create_test_file(target=node, user=node.creator)

@pytest.mark.django_db
class TestFileMetadataRecordSerializer:

    def test_record_created_post_save(self, node, osf_file):
        # check there's a record for every FileMetadataSchema
        assert FileMetadataSchema.objects.count() > 0
        assert osf_file.records.count() == FileMetadataSchema.objects.count()

        for record in osf_file.records.all().select_related('file'):
            assert record.file == osf_file

    def test_serialize_record_datacite(self, node, osf_file):
        # Test all of the parts of serialize_json that are auto-generated
        # from relationships and properties on the node and file

        # add a contributor with an ORCID
        contributor = AuthUserFactory()
        contributor.external_identity = {
            'ORCID': {
                '0000-0001-9143-4653': 'VERIFIED'
            }
        }
        contributor.save()
        node.add_contributor(contributor, save=False)

        # add version, subjects, tags, license, and guid
        # version = FileVersionFactory()
        # osf_file.versions.add(version)
        tags = ['fish', 'scale']
        [osf_file.add_tag(tag, auth=Auth(node.creator), save=False) for tag in tags]

        bepress_subject = SubjectFactory(text='BePress Text')
        new_subject = SubjectFactory(bepress_subject=bepress_subject)
        node.subjects.add(new_subject)

        no_license = NodeLicense.objects.get(name='CC0 1.0 Universal')
        license_detail = {
            'id': no_license.license_id,
            'year': '2018',
            'copyrightHolders': ['Woop', 'Yeah']
        }
        set_license(node, license_detail, Auth(node.creator))

        osf_file.save()
        node.save()

        # create a guid
        Guid.objects.create(
            object_id=osf_file.id,
            content_type_id=ContentType.objects.get_for_model(osf_file).id
        )

        record = osf_file.records.get(schema___id='datacite')
        serialized_record = json.loads(record.serialize())

        # test titles
        titles = [title['title'] for title in serialized_record['titles']]
        assert osf_file.name in titles
        assert node.title in titles

        # test dates
        dates = [date['date'] for date in serialized_record['dates']]
        assert str(osf_file.created) in dates
        assert str(osf_file.modified) in dates
        assert str(osf_file.created.year) == serialized_record['publicationYear']

        # no resource type provided
        assert serialized_record['resourceType']['resourceType'] == '(:unas)'
        assert serialized_record['resourceType']['resourceTypeGeneral'] == 'Other'

        # guid in alternate identifiers
        file_guid = osf_file.guids.first()._id
        alternate_identifier = serialized_record['alternateIdentifiers'][0]
        assert file_guid in alternate_identifier['alternateIdentifier']

        # check for tags and subjects
        subjects_in_record = [sub['subject'] for sub in serialized_record['subjects']]
        assert bepress_subject.text in subjects_in_record
        for tag in tags:
            assert tag in subjects_in_record

        # node license
        rights = serialized_record['rightsList'][0]
        assert rights['rights'] == no_license.name
        assert rights['rightsURI'] == no_license.url

        # test most recent version
        assert serialized_record['version'] == osf_file.versions.first().identifier

    # TODO - not sure how this test should go cause validate calls serialize directly
    # def test_validate_record(self, node, osf_file):
    #     # valid data with no identifier
    #     record = osf_file.records.first()
    #     json_data = record.serialize()
    #     assert record.validate() is None

    #     # make sure another validation error raises
    #     del json_data['titles']
    #     record.metadata = json_data
    #     with pytest.raises(jsonschema.ValidationError) as exc:
    #         record.validate()
    #     assert 'titles' in exc.value.message


@pytest.mark.django_db
class TestFileMetadataRecord:

    @pytest.fixture
    def initial_metadata(self):
        return {
            'file_description': 'Hello this is a description',
            'resource_type': 'Book',
            'related_publication_doi': '10.123/fkosf/hello'
        }

    def test_update_record(self, node, osf_file, initial_metadata):
        record = osf_file.records.first()
        record.metadata = initial_metadata
        record.save()

        new_metadata = {
            'funders': [
                {'funding_agency': 'Hello'},
                {'funding_agency': 'Ric Flair', 'grant_number': 'Woooooo'},
            ]
        }
        record.update(new_metadata, user=node.creator)

        # Make sure an update creates a node log
        assert node.logs.latest().action == NodeLog.FILE_METADATA_UPDATED

        # Make sure old fields are cleared
        assert initial_metadata.keys() not in record.metadata.keys()

    def test_update_fails_with_incorrect_metadata(self, node, osf_file):
        record = osf_file.records.first()

        # TODO - make this an API test?
        # metadata not in schema fails
        wrong_metadata = {
            'favorite_schema': 'crossref'
        }
        with pytest.raises(jsonschema.ValidationError):
            record.update(wrong_metadata, user=node.creator)
        record.reload()
        assert record.metadata == {}
        assert node.logs.latest().action != NodeLog.FILE_METADATA_UPDATED

        # metadata not matching schema pattern fails
        wrong_doi = {
            'related_publication_doi': 'whatever'
        }
        with pytest.raises(jsonschema.ValidationError):
            record.update(wrong_doi, user=node.creator)
        record.reload()
        assert record.metadata == {}
        assert node.logs.latest().action != NodeLog.FILE_METADATA_UPDATED

    def test_update_permissions(self, node, osf_file, initial_metadata):
        record = osf_file.records.first()

        # Can't update with non-contributor auth
        rando = AuthUserFactory()
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=rando)

        # Can't update with read-only auth
        read_contrib = AuthUserFactory()
        node.add_contributor(read_contrib, permissions=['read'])
        node.save()
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=read_contrib)

        # Can't update with no auth
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=None)

    def test_forked_file_has_metadata_copied(self, node, osf_file, initial_metadata):
        record = osf_file.records.first()
        record.metadata = initial_metadata
        record.save()
        fork = node.fork_node(auth=Auth(node.creator))

        forked_record = fork.files.first().records.first()
        assert forked_record.metadata == record.metadata
