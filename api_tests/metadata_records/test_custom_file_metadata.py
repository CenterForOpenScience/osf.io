import pytest
import rdflib

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf.metadata.rdfutils import graph_equals, guid_irl, DCT
from osf.models import PreprintLog, NodeLog, GuidMetadataRecord
from osf.utils.permissions import READ
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
)


@pytest.fixture()
def user_admin():
    return AuthUserFactory()


@pytest.fixture()
def preprint(user_admin):
    return PreprintFactory(creator=user_admin)


@pytest.fixture()
def preprint_record(preprint):
    primary_file = preprint.primary_file
    guid = primary_file.get_guid(create=True)
    return GuidMetadataRecord.objects.for_guid(guid)


@pytest.mark.django_db
class TestCustomFileMetadataRecordDetail:

    @pytest.fixture()
    def private_record(self, user_admin):
        private_node = ProjectFactory(creator=user_admin)
        private_file = utils.create_test_file(private_node, user_admin, filename='private_file')
        return GuidMetadataRecord.objects.for_guid(private_file.get_guid())

    @pytest.fixture()
    def public_record(self, user_admin):
        public_node = ProjectFactory(creator=user_admin, is_public=True)
        public_file = utils.create_test_file(public_node, user_admin, filename='public_file')
        return GuidMetadataRecord.objects.for_guid(public_file.get_guid())

    @pytest.fixture()
    def unpublished_preprint_record(self, user_admin):
        unpublished_preprint = PreprintFactory(is_published=False, creator=user_admin, is_public=False)
        file_guid = unpublished_preprint.primary_file.get_guid(create=True)
        return GuidMetadataRecord.objects.for_guid(file_guid)

    def get_url(self, record):
        return f'/{API_BASE}custom_file_metadata_records/osfio:{record.guid._id}/'

    def test_metadata_record_detail(self, app, user_admin, public_record, private_record):

        # test_unauthenticated_can_view_public_file_metadata_record
        res = app.get(self.get_url(public_record))
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record.guid._id

        # test_authenticated_can_view_public_file_metadata_record
        res = app.get(self.get_url(public_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record.guid._id

        # test_unauthenticated_cannot_view_private_file_metadata_record
        res = app.get(self.get_url(private_record), expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_view_private_file_metadata_record
        res = app.get(self.get_url(private_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == private_record.guid._id

        # test_unauthorized_cannot_view_private_file_metadata_record
        unauth = AuthUserFactory()
        res = app.get(self.get_url(private_record), auth=unauth.auth, expect_errors=True)
        assert res.status_code == 403

        # test_cannot_delete_metadata_records
        res = app.delete_json_api(self.get_url(public_record), auth=user_admin.auth, expect_errors=True)
        assert res.status_code == 405

    def test_preprint_file_metadata_record(self, app, user_admin, preprint_record, unpublished_preprint_record):

        # unauthenticated view public preprint file metadata record
        res = app.get(self.get_url(preprint_record))
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_record.guid._id

        # authenticated view public preprint file metadata record
        res = app.get(self.get_url(preprint_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_record.guid._id

        # unauthenticated cannot view unpublished preprint file metadata record
        res = app.get(self.get_url(unpublished_preprint_record), expect_errors=True)
        assert res.status_code == 401

        # authenticated contributor can view unpublished preprint file metadata record
        res = app.get(self.get_url(unpublished_preprint_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == unpublished_preprint_record.guid._id


@pytest.mark.django_db
class TestFileMetadataRecordUpdate:

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_record(self, user_admin):
        registration = RegistrationFactory(project=ProjectFactory(creator=user_admin))
        registration_file = utils.create_test_file(registration, user_admin, filename='registration_file')
        return GuidMetadataRecord.objects.for_guid(registration_file.get_guid())

    @pytest.fixture()
    def node(self, user_admin):
        return ProjectFactory(creator=user_admin, is_public=True)

    @pytest.fixture()
    def public_file_guid(self, user_admin, node, user_write, user_read):
        node.add_contributor(user_write)
        node.add_contributor(user_read, permissions=READ)
        public_file = utils.create_test_file(node, user_admin, filename='public_file')
        return public_file.get_guid()

    def get_url(self, guid):
        return f'/{API_BASE}custom_file_metadata_records/osfio:{guid._id}/'

    # @pytest.fixture()
    # def metadata_record_json(self):
    #     return {
    #         'file_description': 'Plot of change over time',
    #         'related_publication_doi': '10.1025/osf.io/abcde',
    #         'funders': [
    #             {'funding_agency': 'LJAF'},
    #             {'funding_agency': 'Templeton', 'grant_number': '12345'},
    #         ]
    #     }

    def make_payload(self, guid, **attributes):
        return {
            'data': {
                'id': guid._id,
                'type': 'metadata_records',
                'attributes': attributes,
            }
        }

    def test_admin_can_update(self, app, user_admin, node, public_file_guid):
        payload = self.make_payload(public_file_guid, language='nga-CD')
        res = app.patch_json_api(self.get_url(public_file_guid), payload, auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['language'] == 'nga-CD'
        saved_custom_metadata = public_file_guid.metadata_record.custom_metadata
        assert graph_equals(saved_custom_metadata, [
            (guid_irl(public_file_guid), DCT.language, rdflib.Literal('nga-CD')),
        ])
        # assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    def test_write_can_update(self, app, user_write, public_file_guid):
        payload = self.make_payload(
            public_file_guid,
            title='my file',
            description='this is my file',
            language='en-NZ',
            resource_type_general='Text',
        )
        res = app.patch_json_api(self.get_url(public_file_guid), payload, auth=user_write.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes'] == {
            'title': 'my file',
            'description': 'this is my file',
            'language': 'en-NZ',
            'resource_type_general': 'Text',
        }
        saved_custom_metadata = public_file_guid.metadata_record.custom_metadata
        guid_uri = guid_irl(public_file_guid)
        assert graph_equals(saved_custom_metadata, [
            (guid_uri, DCT.language, rdflib.Literal('en-NZ')),
            (guid_uri, DCT.title, rdflib.Literal('my file')),
            (guid_uri, DCT.description, rdflib.Literal('this is my file')),
            (guid_uri, DCT.type, rdflib.Literal('Text')),
        ])
        # assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    # def test_read_cannot_update(self, app, user_read, public_record, make_payload):
    #     res = app.patch_json_api(self.get_url(public_record), make_payload(public_record), auth=user_read.auth, expect_errors=True)
    #     assert res.status_code == 403

    # def test_update_fails_with_extra_key(self, app, user, public_record, make_payload):
    #     payload = make_payload(public_record)
    #     payload['data']['attributes']['metadata']['cat'] = 'sterling'
    #     res = app.patch_json_api(self.get_url(public_record), payload, auth=user.auth, expect_errors=True)
    #     public_record.reload()
    #     assert res.status_code == 400
    #     assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
    #     assert res.json['errors'][0]['meta'].get('metadata_schema', None)
    #     assert public_record.metadata == {}

    # def test_update_fails_with_invalid_json(self, app, user, public_record, make_payload):
    #     payload = make_payload(public_record)
    #     payload['data']['attributes']['metadata']['related_publication_doi'] = 'dinosaur'
    #     res = app.patch_json_api(self.get_url(public_record), payload, auth=user.auth, expect_errors=True)
    #     public_record.reload()
    #     assert res.status_code == 400
    #     assert res.json['errors'][0]['detail'] == 'Your response of dinosaur for the field related_publication_doi was invalid.'
    #     assert public_record.metadata == {}

    # def test_cannot_update_registration_metadata_record(self, app, user, registration_record, make_payload):
    #     url = '/{}files/{}/metadata_records/{}/'.format(API_BASE, registration_record.file._id, registration_record._id)
    #     res = app.patch_json_api(url, make_payload(registration_record), auth=user.auth, expect_errors=True)
    #     assert res.status_code == 403

    # def test_update_file_metadata_for_preprint_file(self, app, user, metadata_record_json, make_payload, preprint_record, preprint):
    #     res = app.patch_json_api(self.get_url(preprint_record), make_payload(preprint_record), auth=user.auth)
    #     preprint_record.reload()
    #     assert res.status_code == 200
    #     assert res.json['data']['attributes']['metadata'] == metadata_record_json
    #     assert preprint_record.metadata == metadata_record_json
    #     assert preprint.logs.first().action == PreprintLog.FILE_METADATA_UPDATED
