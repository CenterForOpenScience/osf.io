import pytest
from urllib.parse import urlparse

from api.base.settings import API_BASE, API_PRIVATE_BASE

from .test_record import TestCedarMetadataRecord

from osf.models import CedarMetadataRecord
from osf.utils.permissions import READ, WRITE

from osf_tests.factories import AuthUserFactory

@pytest.mark.django_db
class TestCedarMetadataRecordList(TestCedarMetadataRecord):

    def test_record_list_no_auth(self, app, cedar_draft_record_ids, cedar_published_private_record_ids, cedar_published_public_record_ids):

        resp = app.get('/_/cedar_metadata_records/')
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == len(cedar_published_public_record_ids)
        assert set(cedar_published_public_record_ids) == set([datum['id'] for datum in data])

    def test_record_list_with_invalid_auth(self, app, user_alt, cedar_draft_record_ids, cedar_published_private_record_ids, cedar_published_public_record_ids):

        resp = app.get('/_/cedar_metadata_records/', auth=user_alt.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == len(cedar_published_public_record_ids)
        assert set(cedar_published_public_record_ids) == set([datum['id'] for datum in data])

    # NOTE: Per API contract, we don't actually use this view for listing purpose, thus only published records
    # are returned even user can access the unpublished ones, and thus no need to test read/write/admin separately
    def test_record_list_with_valid_auth(self, app, user, cedar_draft_record_ids, cedar_published_private_record_ids, cedar_published_public_record_ids):

        resp = app.get('/_/cedar_metadata_records/', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        cedar_published_record_ids = cedar_published_public_record_ids + cedar_published_private_record_ids
        assert len(data) == len(cedar_published_record_ids)
        assert set(cedar_published_record_ids) == set([datum['id'] for datum in data])

@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForProjects(TestCedarMetadataRecord):

    @pytest.fixture
    def payload_node(self, cedar_template_alt, cedar_record_metadata_json, node):

        return {
            'data': {
                'type': 'cedar_metadata_records',
                'attributes': {
                    'metadata': cedar_record_metadata_json,
                    'is_published': 'true'
                },
                'relationships': {
                    'template': {
                        'data': {
                            'type': 'cedar-metadata-templates',
                            'id': cedar_template_alt._id
                        }
                    },
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': node._id
                        }
                    }
                }
            }
        }

    def test_record_list_create_for_node_conflict(self, app, user, node, payload_node, cedar_template, cedar_record_metadata_json, cedar_record_for_node):

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

    # TODO: discuss and fix permission
    @pytest.mark.skip(reason='discuss and fix permission')
    def test_record_list_create_for_node_with_read_auth(self, app, node, payload_node):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=read.auth, expect_errors=True)
        assert resp.status_code == 401

    # TODO: discuss and fix permission
    @pytest.mark.skip(reason='discuss and fix permission')
    def test_record_list_create_for_node_with_invalid_auth(self, app, user_alt, node, payload_node):

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 401

    def test_record_list_create_for_node_without_auth(self, app, user_alt, node, payload_node):

        resp = app.post_json('/_/cedar_metadata_records/', payload_node, auth=None, expect_errors=True)
        assert resp.status_code == 401

@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForRegistrations(TestCedarMetadataRecord):
    # TODO: implement this
    pass

@pytest.mark.django_db
class TestCedarMetadataRecordListCreateForFiles(TestCedarMetadataRecord):
    # TODO: implement this
    pass
