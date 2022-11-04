import pytest
import rdflib

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf.metadata.rdfutils import graph_equals, DCT
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
def preprint_guid(preprint):
    return preprint.guids.first()


def get_url(guid):
    if hasattr(guid, 'guid'):
        guid = guid.guid
    return f'/{API_BASE}custom_item_metadata_records/osfio:{guid._id}/'


@pytest.mark.django_db
class TestCustomItemMetadataRecordDetail:

    @pytest.fixture()
    def private_record(self, user_admin):
        private_node = ProjectFactory(creator=user_admin)
        return GuidMetadataRecord.objects.for_guid(private_node._id)

    @pytest.fixture()
    def public_record(self, user_admin):
        public_node = ProjectFactory(creator=user_admin, is_public=True)
        return GuidMetadataRecord.objects.for_guid(public_node._id)

    @pytest.fixture()
    def unpublished_preprint_guid(self, user_admin):
        unpublished_preprint = PreprintFactory(is_published=False, creator=user_admin, is_public=False)
        return unpublished_preprint.guids.first()

    def test_metadata_record_detail(self, app, user_admin, public_record, private_record):

        # test_unauthenticated_can_view_public_item_metadata_record
        res = app.get(get_url(public_record))
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record.guid._id

        # test_authenticated_can_view_public_item_metadata_record
        res = app.get(get_url(public_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == public_record.guid._id

        # test_unauthenticated_cannot_view_private_item_metadata_record
        res = app.get(get_url(private_record), expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_view_private_item_metadata_record
        res = app.get(get_url(private_record), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == private_record.guid._id

        # test_unauthorized_cannot_view_private_item_metadata_record
        unauth = AuthUserFactory()
        res = app.get(get_url(private_record), auth=unauth.auth, expect_errors=True)
        assert res.status_code == 403

        # test_cannot_delete_metadata_records
        res = app.delete_json_api(get_url(public_record), auth=user_admin.auth, expect_errors=True)
        assert res.status_code == 405

    def test_preprint_metadata_record(self, app, user_admin, preprint_guid, unpublished_preprint_guid):

        # unauthenticated view public preprint metadata record
        res = app.get(get_url(preprint_guid))
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_guid._id

        # authenticated view public preprint metadata record
        res = app.get(get_url(preprint_guid), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == preprint_guid._id

        # unauthenticated cannot view unpublished preprint metadata record
        res = app.get(get_url(unpublished_preprint_guid), expect_errors=True)
        assert res.status_code == 401

        # authenticated contributor can view unpublished preprint metadata record
        res = app.get(get_url(unpublished_preprint_guid), auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == unpublished_preprint_guid._id


@pytest.mark.django_db
class TestCustomFileMetadataRecordUpdate:

    @pytest.fixture()
    def user_write(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_record(self, user_admin):
        registration = RegistrationFactory(project=ProjectFactory(creator=user_admin))
        return GuidMetadataRecord.objects.for_guid(registration._id)

    @pytest.fixture()
    def node(self, user_admin):
        return ProjectFactory(creator=user_admin, is_public=True)

    @pytest.fixture()
    def public_node_guid(self, user_admin, node, user_write, user_read):
        node.add_contributor(user_write)
        node.add_contributor(user_read, permissions=READ)
        return node.guids.first()

    def make_payload(self, guid, **attributes):
        return {
            'data': {
                'id': guid._id,
                'type': 'custom-item-metadata-records',
                'attributes': attributes,
            }
        }

    def test_admin_can_update(self, app, user_admin, node, public_node_guid):
        payload = self.make_payload(public_node_guid, language='nga-CD')
        res = app.patch_json_api(get_url(public_node_guid), payload, auth=user_admin.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['language'] == 'nga-CD'
        metadata_record = public_node_guid.metadata_record
        assert graph_equals(metadata_record.custom_metadata, [
            (metadata_record.guid_uri, DCT.language, rdflib.Literal('nga-CD')),
        ])
        # assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    def test_write_can_update(self, app, user_write, public_node_guid):
        payload = self.make_payload(
            public_node_guid,
            title='tryna pull something',
            description='title and description cannot be set this way',
            language='en-NZ',
            resource_type_general='Text',
        )
        res = app.patch_json_api(get_url(public_node_guid), payload, auth=user_write.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes'] == {
            'language': 'en-NZ',
            'resource_type_general': 'Text',
        }
        metadata_record = public_node_guid.metadata_record
        guid_uri = metadata_record.guid_uri
        assert graph_equals(metadata_record.custom_metadata, [
            (guid_uri, DCT.language, rdflib.Literal('en-NZ')),
            (guid_uri, DCT.type, rdflib.Literal('Text')),
        ])
        # assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    def test_read_cannot_update(self, app, user_read, public_node_guid):
        payload = self.make_payload(public_node_guid, language='nga-CD')
        res = app.patch_json_api(get_url(public_node_guid), payload, auth=user_read.auth, expect_errors=True)
        assert res.status_code == 403

    # def test_update_fails_with_extra_key(self, app, user_write, public_file_guid):
    #     payload = self.make_payload(
    #         public_file_guid,
    #         cat='mackerel',
    #     )
    #     res = app.patch_json_api(get_url(public_file_guid), payload, auth=user_write.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
    #     assert res.json['errors'][0]['meta'].get('metadata_schema', None)
    #     # assert public_record.metadata == {}

    # def test_update_fails_with_invalid_json(self, app, user, public_record, make_payload):
    #     payload = make_payload(public_record)
    #     payload['data']['attributes']['metadata']['related_publication_doi'] = 'dinosaur'
    #     res = app.patch_json_api(get_url(public_record), payload, auth=user.auth, expect_errors=True)
    #     public_record.reload()
    #     assert res.status_code == 400
    #     assert res.json['errors'][0]['detail'] == 'Your response of dinosaur for the field related_publication_doi was invalid.'
    #     assert public_record.metadata == {}

    # def test_cannot_update_registration_metadata_record(self, app, user, registration_record, make_payload):
    #     url = '/{}files/{}/metadata_records/{}/'.format(API_BASE, registration_record.file._id, registration_record._id)
    #     res = app.patch_json_api(url, make_payload(registration_record), auth=user.auth, expect_errors=True)
    #     assert res.status_code == 403

    # def test_update_file_metadata_for_preprint_file(self, app, user_write, preprint_record, preprint):
    #     res = app.patch_json_api(get_url(preprint_record), make_payload(preprint_record), auth=user.auth)
    #     preprint_record.reload()
    #     assert res.status_code == 200
    #     assert res.json['data']['attributes']['metadata'] == metadata_record_json
    #     assert preprint_record.metadata == metadata_record_json
    #     assert preprint.logs.first().action == PreprintLog.FILE_METADATA_UPDATED
