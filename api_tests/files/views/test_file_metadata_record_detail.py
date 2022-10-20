import pytest

from api.base.settings.defaults import API_BASE
from osf.models import PreprintLog, NodeLog
from api_tests import utils
from osf.utils.permissions import READ
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
)

from osf.migrations import ensure_datacite_file_schema


@pytest.fixture(autouse=True)
def datacite_file_schema():
    return ensure_datacite_file_schema()


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def preprint(user):
    return PreprintFactory(creator=user)


@pytest.fixture()
def preprint_record(user, preprint):
    primary_file = preprint.primary_file
    return primary_file.records.get(schema___id='datacite')


@pytest.mark.django_db
class TestFileMetadataRecordDetail:

    @pytest.fixture()
    def private_record(self, user):
        private_node = ProjectFactory(creator=user)
        private_file = utils.create_test_file(private_node, user, filename='private_file')
        return private_file.records.get(schema___id='datacite')

    @pytest.fixture()
    def public_record(self, user):
        public_node = ProjectFactory(creator=user, is_public=True)
        public_file = utils.create_test_file(public_node, user, filename='public_file')
        return public_file.records.get(schema___id='datacite')

    @pytest.fixture()
    def unpublished_preprint_record(self, user):
        unpublished_preprint = PreprintFactory(is_published=False, creator=user, is_public=False)
        return unpublished_preprint.primary_file.records.get(schema___id='datacite')

    def get_url(self, record):
        return '/{}files/{}/metadata_records/{}/'.format(API_BASE, record.file._id, record._id)

    def test_metadata_record_detail(self, app, user, public_record, private_record):

        # test_unauthenticated_can_view_public_file_metadata_record
        res = app.get(self.get_url(public_record))
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record._id

        # test_authenticated_can_view_public_file_metadata_record
        res = app.get(self.get_url(public_record), auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record._id

        # test_unauthenticated_cannot_view_private_file_metadata_record
        res = app.get(self.get_url(private_record), expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_view_private_file_metadata_record
        res = app.get(self.get_url(private_record), auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == private_record._id

        # test_unauthorized_cannot_view_private_file_metadata_record
        unauth = AuthUserFactory()
        res = app.get(self.get_url(private_record), auth=unauth.auth, expect_errors=True)
        assert res.status_code == 403

        # test_cannot_delete_metadata_records
        res = app.delete_json_api(self.get_url(public_record), auth=user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_preprint_file_metadata_record(self, app, user, preprint_record, unpublished_preprint_record):

        # unauthenticated view public preprint file metadata record
        res = app.get(self.get_url(preprint_record))
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_record._id

        # authenticated view public preprint file metadata record
        res = app.get(self.get_url(preprint_record), auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_record._id

        # unauthenticated cannot view unpublished preprint file metadata record
        res = app.get(self.get_url(unpublished_preprint_record), expect_errors=True)
        assert res.status_code == 401

        # authenticated contributor can view unpublished preprint file metadata record
        res = app.get(self.get_url(unpublished_preprint_record), auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == unpublished_preprint_record._id


@pytest.mark.django_db
class TestFileMetadataRecordUpdate:

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_record(self, user):
        registration = RegistrationFactory(project=ProjectFactory(creator=user))
        registration_file = utils.create_test_file(registration, user, filename='registration_file')
        return registration_file.records.get(schema___id='datacite')

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def public_record(self, user, node, user_write, user_read):
        node.add_contributor(user_write)
        node.add_contributor(user_read, permissions=READ)
        public_file = utils.create_test_file(node, user, filename='public_file')
        return public_file.records.get(schema___id='datacite')

    def get_url(self, record):
        return '/{}files/{}/metadata_records/{}/'.format(API_BASE, record.file._id, record._id)

    @pytest.fixture()
    def metadata_record_json(self):
        return {
            'file_description': 'Plot of change over time',
            'related_publication_doi': '10.1025/osf.io/abcde',
            'funders': [
                {'funding_agency': 'LJAF'},
                {'funding_agency': 'Templeton', 'grant_number': '12345'},
            ]
        }

    @pytest.fixture()
    def make_payload(self, metadata_record_json):
        def payload(record, metadata=None, relationships=None):
            payload_data = {
                'data': {
                    'id': record._id,
                    'type': 'metadata_records',
                    'attributes': {
                        'metadata': metadata_record_json if not metadata else metadata
                    }
                }
            }
            if relationships:
                payload_data['data']['relationships'] = relationships

            return payload_data
        return payload

    def test_admin_can_update(self, app, user, node, public_record, make_payload, metadata_record_json):
        res = app.patch_json_api(self.get_url(public_record), make_payload(public_record), auth=user.auth)
        public_record.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['metadata'] == metadata_record_json
        assert public_record.metadata == metadata_record_json
        assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    def test_write_can_update(self, app, user_write, public_record, make_payload, metadata_record_json):
        res = app.patch_json_api(self.get_url(public_record), make_payload(public_record), auth=user_write.auth)
        public_record.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['metadata'] == metadata_record_json
        assert public_record.metadata == metadata_record_json

    def test_read_cannot_update(self, app, user_read, public_record, make_payload):
        res = app.patch_json_api(self.get_url(public_record), make_payload(public_record), auth=user_read.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_fails_with_extra_key(self, app, user, public_record, make_payload):
        payload = make_payload(public_record)
        payload['data']['attributes']['metadata']['cat'] = 'sterling'
        res = app.patch_json_api(self.get_url(public_record), payload, auth=user.auth, expect_errors=True)
        public_record.reload()
        assert res.status_code == 400
        assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
        assert res.json['errors'][0]['meta'].get('metadata_schema', None)
        assert public_record.metadata == {}

    def test_update_fails_with_invalid_json(self, app, user, public_record, make_payload):
        payload = make_payload(public_record)
        payload['data']['attributes']['metadata']['related_publication_doi'] = 'dinosaur'
        res = app.patch_json_api(self.get_url(public_record), payload, auth=user.auth, expect_errors=True)
        public_record.reload()
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Your response of dinosaur for the field related_publication_doi was invalid.'
        assert public_record.metadata == {}

    def test_cannot_update_registration_metadata_record(self, app, user, registration_record, make_payload):
        url = '/{}files/{}/metadata_records/{}/'.format(API_BASE, registration_record.file._id, registration_record._id)
        res = app.patch_json_api(url, make_payload(registration_record), auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_file_metadata_for_preprint_file(self, app, user, metadata_record_json, make_payload, preprint_record, preprint):
        res = app.patch_json_api(self.get_url(preprint_record), make_payload(preprint_record), auth=user.auth)
        preprint_record.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['metadata'] == metadata_record_json
        assert preprint_record.metadata == metadata_record_json
        assert preprint.logs.first().action == PreprintLog.FILE_METADATA_UPDATED
