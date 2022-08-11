import json
import pytest
import jsonschema

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from website.settings import DOI_FORMAT, DATACITE_PREFIX
from website.project.licenses import set_license
from osf.models import FileMetadataSchema, NodeLicense, NodeLog
from osf.migrations import ensure_datacite_file_schema
from osf_tests.factories import ProjectFactory, SubjectFactory, AuthUserFactory
from osf.utils.permissions import READ
from api_tests.utils import create_test_file


@pytest.fixture(autouse=True)
def datacite_file_schema():
    return ensure_datacite_file_schema()


@pytest.fixture()
def node():
    return ProjectFactory()


@pytest.fixture()
def osf_file(node):
    return create_test_file(target=node, user=node.creator)


def inject_placeholder_doi(json_data):
    # the OSF cannot currently issue DOIs for a file, which is required for datacite schema validation.
    # Manually add a placeholder in tests for validation until we handle this better.
    placeholder = DOI_FORMAT.format(prefix=DATACITE_PREFIX, guid='placeholder')
    json_data['identifier'] = {'identifierType': 'DOI', 'identifier': placeholder}
    return json_data


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

        # add subjects, tags, license, and guid
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
        osf_file.target.reload()

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

    def test_validate(self, node, osf_file):
        record = osf_file.records.get(schema___id='datacite')
        json_data = json.loads(record.serialize())

        assert jsonschema.validate(
            inject_placeholder_doi(json_data),
            record.schema.schema
        ) is None


@pytest.mark.django_db
class TestFileMetadataRecord:

    @pytest.fixture()
    def initial_metadata(self):
        return {
            'file_description': 'Hello this is a description',
            'resource_type': 'Book',
            'related_publication_doi': '10.123/fkosf/hello'
        }

    @pytest.fixture()
    def record(self, osf_file):
        return osf_file.records.first()

    def test_update_record(self, node, record, initial_metadata):
        record.metadata = initial_metadata
        record.save()

        partial_metadata = {
            'funders': [
                {'funding_agency': 'Hello'},
                {'funding_agency': 'Ric Flair', 'grant_number': 'Woooooo'},
            ]
        }
        record.update(partial_metadata, user=node.creator)

        # Make sure an update creates a node log
        assert node.logs.latest().action == NodeLog.FILE_METADATA_UPDATED

        # Make sure old fields are cleared
        assert list(initial_metadata.keys()) not in list(record.metadata.keys())

        full_metadata = {
            'funders': [
                {'funding_agency': 'Hello'},
                {'funding_agency': 'Ric Flair', 'grant_number': 'Woooooo'},
            ],
            'file_description': 'Hey this is a great interesting important file',
            'resource_type': 'Funding Submission',
            'related_publication_doi': '10.12345/fk2osf.io/hello/'
        }
        record.update(full_metadata, user=node.creator)

        json_data = json.loads(record.serialize())
        datacite_user_entered_fields = ['fundingReferences', 'resourceType', 'descriptions', 'relatedIdentifiers']
        for field in datacite_user_entered_fields:
            assert field in json_data.keys()

        # validate record with all user entered metadata
        assert jsonschema.validate(
            inject_placeholder_doi(json_data),
            record.schema.schema
        ) is None

    def test_update_fails_with_incorrect_metadata(self, node, record):
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

        # resource_type not in specified options fails
        wrong_resource_type = {
            'resource_type': 'Scrap Book'
        }
        with pytest.raises(jsonschema.ValidationError):
            record.update(wrong_resource_type, user=node.creator)

        # funders but no funding agency
        no_funding_agency_metadata = {
            'funders': [
                {'grant_number': 'Woooo'}
            ]
        }
        with pytest.raises(jsonschema.ValidationError):
            record.update(no_funding_agency_metadata, user=node.creator)

        # additional properties for funders fails
        more_funders_metadata = {
            'funders': [
                {'funding_agency': 'Woop', 'there_it': 'is'}
            ]
        }
        with pytest.raises(jsonschema.ValidationError):
            record.update(more_funders_metadata, user=node.creator)

    def test_update_permissions(self, node, record, initial_metadata):
        # Can't update with non-contributor auth
        rando = AuthUserFactory()
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=rando)

        # Can't update with read-only auth
        read_contrib = AuthUserFactory()
        node.add_contributor(read_contrib, permissions=READ)
        node.save()
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=read_contrib)

        # Can't update with no auth
        with pytest.raises(PermissionsError):
            record.update(initial_metadata, user=None)

    def test_forked_file_has_metadata_copied(self, node, record, initial_metadata):
        record.metadata = initial_metadata
        record.save()
        fork = node.fork_node(auth=Auth(node.creator))

        forked_record = fork.files.first().records.first()
        assert forked_record.metadata == record.metadata
