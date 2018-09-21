import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
)


@pytest.mark.django_db
class TestFileMetadataRecordDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def private_file(self, user, private_node):
        return utils.create_test_file(private_node, user, filename='private_file')

    @pytest.fixture()
    def private_record(self, user, private_file):
        return private_file.records.first()

    @pytest.fixture()
    def private_record_url(self, private_file, private_record):
        return '/{}files/{}/metadata_records/{}/'.format(API_BASE, private_file._id, private_record._id)

    @pytest.fixture()
    def public_node(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def public_file(self, user, public_node):
        return utils.create_test_file(public_node, user, filename='public_file')

    @pytest.fixture()
    def public_record(self, user, public_file):
        return public_file.records.first()

    @pytest.fixture()
    def public_record_url(self, public_file, public_record):
        return '/{}files/{}/metadata_records/{}/'.format(API_BASE, public_file._id, public_record._id)

    def test_metadata_record_detail(self, app, user, public_record, private_record, public_record_url, private_record_url):

        # test_unauthenticated_can_view_public_file_metadata_record
        res = app.get(public_record_url)
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record._id

        # test_authenticated_can_view_public_file_metadata_record
        res = app.get(public_record_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record._id

        # test_unauthenticated_cannot_view_private_file_metadata_record
        res = app.get(private_record_url, expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_view_private_file_metadata_record
        res = app.get(private_record_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == private_record._id

        # test_unauthorized_cannot_view_private_file_metadata_record
        unauth = AuthUserFactory()
        res = app.get(private_record_url, auth=unauth.auth, expect_errors=True)
        assert res.status_code == 403

        # test_cannot_delete_metadata_records
        res = app.delete_json_api(public_record_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405


@pytest.mark.django_db
class TestFileMetadataRecordUpdate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_node(self, user, user_write, user_read):
        node = ProjectFactory(creator=user, is_public=True)
        node.add_contributor(user_write)
        node.add_contributor(user_read)
        return node

    @pytest.fixture()
    def registration_file(self, user, public_node):
        registration = RegistrationFactory(project=public_node)
        return utils.create_test_file(registration, user, filename='registration_file')

    @pytest.fixture()
    def registration_record(self, user, registration_file):
        return registration_file.records.first()

    @pytest.fixture()
    def public_file(self, user, public_node):
        return utils.create_test_file(public_node, user, filename='public_file')

    @pytest.fixture()
    def public_record(self, user, public_file):
        return public_file.records.first()

    @pytest.fixture()
    def public_record_url(self, public_file):
        record = public_file.records.first()
        return '/{}files/{}/metadata_records/{}/'.format(API_BASE, public_file._id, record._id)

    @pytest.fixture()
    def metadata_record_json(self):
        return {
            'file_description': 'Plot of change over time',
            'related_publication_doi': '10.1025/osf.io/abcde'
            # 'funding_agency': 'LJAF',
            # 'grant_number': '123456'
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

    def test_metadata_record_update(self, app, user, user_write, user_read, public_record, public_record_url, make_payload, metadata_record_json):

        # test_admin_contributor_can_update_metadata_record
        res = app.patch_json_api(public_record_url, make_payload(public_record), auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['metadata'] == metadata_record_json
        assert public_record.metadata == metadata_record_json

        # test_write_contributor_can_update_metadata_record
        res = app.patch_json_api(public_record_url, make_payload(public_record), auth=user_write.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['metadata'] == metadata_record_json
        assert public_record.metadata == metadata_record_json

        # test_read_contributor_cannot_update_metadata_record
        res = app.patch_json_api(public_record_url, make_payload(public_record), auth=user_write.auth, expect_errors=True)
        assert res.status_code == 403

        # test_metadata_record_with_extra_key_fails
        extra_payload = make_payload(public_record)
        extra_payload['data']['attributes']['metadata']['cat'] = ['sterling']
        res = app.patch_json_api(public_record_url, extra_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
        assert public_record.metadata == {}

        # test_metadata_record_with_invalid_json_fails
        invalid_payload = make_payload(public_record)
        invalid_payload['data']['attributes']['metadata']['related_publication_doi'] = ['dinosaur']
        res = app.patch_json_api(public_record_url, invalid_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'assert the correct error here' in res.json['errors'][0]['detail']
        assert public_record.metadata == {}

    def test_cannot_update_registration_metadata_record(self, app, user, registration_file, registration_record, make_payload):
        url = '/{}files/{}/metadata_records/{}/'.format(API_BASE, registration_file._id, registration_record._id)
        res = app.patch_json_api(url, make_payload(registration_record), auth=user.auth, expect_errors=True)
        assert res.status_code == 403
