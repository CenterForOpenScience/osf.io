import pytest
from urllib.parse import urlparse

from .test_record import TestCedarMetadataRecord
from api.base.settings import API_BASE, API_PRIVATE_BASE
from osf.models import CedarMetadataRecord
from osf.utils.permissions import READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForProjects(TestCedarMetadataRecord):

    def test_record_list_create_for_node_with_inactive_template(self, app, user, payload_node, cedar_template_inactive):

        payload = payload_node
        payload['data']['relationships']['template']['data']['id'] = cedar_template_inactive._id
        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=user.auth, expect_errors=True)
        assert resp.status_code == 404

    def test_record_list_create_for_node_conflict(self, app, user, node, payload_node, cedar_template, cedar_record_for_node):

        record = CedarMetadataRecord.objects.get(guid___id=node._id, template___id=cedar_template._id)
        assert record == cedar_record_for_node
        payload = payload_node
        payload['data']['relationships']['template']['data']['id'] = cedar_template._id
        resp = app.post_json('/_/cedar_metadata_records/', payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400

    def test_record_list_create_for_node_with_admin_auth(self, app, user, node, payload_node, cedar_template_alt, cedar_record_metadata_json):

        admin = user
        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=admin.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': node._id, 'type': 'nodes'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}nodes/{node._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_node_with_write_contributor_auth(self, app, node, payload_node, cedar_template_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=write.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': node._id, 'type': 'nodes'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}nodes/{node._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_node_with_read_auth(self, app, node, payload_node):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_node_with_invalid_auth(self, app, user_alt, payload_node):

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_node_without_auth(self, app, payload_node):

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=None, expect_errors=True)
        assert resp.status_code == 401

@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForRegistrations(TestCedarMetadataRecord):

    def test_record_list_create_for_node_with_inactive_template(self, app, user, payload_registration, cedar_template_inactive):
        payload = payload_registration
        payload['data']['relationships']['template']['data']['id'] = cedar_template_inactive._id
        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=user.auth, expect_errors=True)
        assert resp.status_code == 404

    def test_record_list_create_for_registration_conflict(self, app, user, registration, payload_registration, cedar_template, cedar_record_for_registration):

        record = CedarMetadataRecord.objects.get(guid___id=registration._id, template___id=cedar_template._id)
        assert record == cedar_record_for_registration
        payload = payload_registration
        payload['data']['relationships']['template']['data']['id'] = cedar_template._id
        resp = app.post_json('/_/cedar_metadata_records/', payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400

    def test_record_list_create_for_node_with_admin_auth(self, app, user, registration, payload_registration, cedar_template_alt, cedar_record_metadata_json):

        admin = user
        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=admin.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': registration._id, 'type': 'registrations'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}registrations/{registration._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_node_with_write_contributor_auth(self, app, registration, payload_registration, cedar_template_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        registration.add_contributor(write, permissions=WRITE)
        registration.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=write.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': registration._id, 'type': 'registrations'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}registrations/{registration._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_node_with_read_auth(self, app, registration, payload_registration):

        read = AuthUserFactory()
        registration.add_contributor(read, permissions=READ)
        registration.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_node_with_invalid_auth(self, app, user_alt, payload_registration):

        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_node_without_auth(self, app, payload_registration):

        resp = app.post_json('/_/cedar_metadata_records/', payload_registration, auth=None, expect_errors=True)
        assert resp.status_code == 401

@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForFiles(TestCedarMetadataRecord):

    def test_record_list_create_for_file_with_inactive_template(self, app, user, payload_file, cedar_template_inactive):

        payload = payload_file
        payload['data']['relationships']['template']['data']['id'] = cedar_template_inactive._id
        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=user.auth, expect_errors=True)
        assert resp.status_code == 404

    def test_record_list_create_for_file_conflict(self, app, user, file, payload_file, cedar_template, cedar_record_for_file):

        record = CedarMetadataRecord.objects.get(guid___id=file.get_guid()._id, template___id=cedar_template._id)
        assert record == cedar_record_for_file
        payload = payload_file
        payload['data']['relationships']['template']['data']['id'] = cedar_template._id
        resp = app.post_json('/_/cedar_metadata_records/', payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400

    def test_record_list_create_for_file_with_admin_auth(self, app, user, file, payload_file, cedar_template_alt, cedar_record_metadata_json):

        admin = user
        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=admin.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': file.get_guid()._id, 'type': 'files'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}files/{file.get_guid()._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_file_with_write_contributor_auth(self, app, node, file, payload_file, cedar_template_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=write.auth)
        assert resp.status_code == 201
        data = resp.json['data']
        record_id = data['id']
        record = CedarMetadataRecord.objects.get(_id=record_id)

        assert data['type'] == 'cedar-metadata-records'
        assert data['attributes']['metadata'] == cedar_record_metadata_json
        assert data['attributes']['is_published'] is True
        relationships = data['relationships']
        assert relationships['target']['data'] == {'id': file.get_guid()._id, 'type': 'files'}
        assert urlparse(relationships['target']['links']['related']['href']).path == f'/{API_BASE}files/{file.get_guid()._id}/'
        assert relationships['template']['data'] == {'id': cedar_template_alt._id, 'type': 'cedar-metadata-templates'}
        assert urlparse(relationships['template']['links']['related']['href']).path == f'/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template_alt._id}/'
        assert urlparse(data['links']['self']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/'
        assert urlparse(data['links']['metadata_download']).path == f'/{API_PRIVATE_BASE}cedar_metadata_records/{record._id}/metadata_download/'

    def test_record_list_create_for_file_with_read_auth(self, app, node, payload_file):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_file_with_invalid_auth(self, app, user_alt, payload_file):

        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_create_for_file_without_auth(self, app, payload_file):

        resp = app.post_json('/_/cedar_metadata_records/', payload_file, auth=None, expect_errors=True)
        assert resp.status_code == 401
