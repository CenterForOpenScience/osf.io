import pytest

from .test_node_cedar_metadata_record import TesNodeCedarMetadataRecord
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestNodeCedarMetadataRecordListPublicProject(TesNodeCedarMetadataRecord):

    def test_record_list_no_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_draft_record_for_node_pub):

        resp = app.get(f'/v2/nodes/{node_pub._id}/cedar_metadata_records/')
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_node_pub._id in data_set
        assert cedar_draft_record_for_node_pub._id not in data_set

    def test_record_list_with_invalid_auth(self, app, user_alt, node_pub, cedar_record_for_node_pub, cedar_draft_record_for_node_pub):

        resp = app.get(f'/v2/nodes/{node_pub._id}/cedar_metadata_records/', auth=user_alt.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_node_pub._id in data_set
        assert cedar_draft_record_for_node_pub._id not in data_set

    def test_record_list_with_read_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_draft_record_for_node_pub):

        read = AuthUserFactory()
        node_pub.add_contributor(read, permissions=READ)
        node_pub.save()
        resp = app.get(f'/v2/nodes/{node_pub._id}/cedar_metadata_records/', auth=read.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_node_pub._id in data_set
        assert cedar_draft_record_for_node_pub._id not in data_set

    def test_record_list_with_write_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_draft_record_for_node_pub):

        write = AuthUserFactory()
        node_pub.add_contributor(write, permissions=WRITE)
        node_pub.save()
        resp = app.get(f'/v2/nodes/{node_pub._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_node_pub._id in data_set
        assert cedar_draft_record_for_node_pub._id in data_set

    def test_record_list_with_admin_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_draft_record_for_node_pub):

        admin = AuthUserFactory()
        node_pub.add_contributor(admin, permissions=ADMIN)
        node_pub.save()
        resp = app.get(f'/v2/nodes/{node_pub._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_node_pub._id in data_set
        assert cedar_draft_record_for_node_pub._id in data_set


@pytest.mark.django_db
class TestNodeCedarMetadataRecordListPrivateProject(TesNodeCedarMetadataRecord):

    def test_record_list_no_auth(self, app, node):

        resp = app.get(f'/v2/nodes/{node._id}/cedar_metadata_records/', expect_errors=True)
        assert resp.status_code == 401

    def test_record_list_with_invalid_auth(self, app, user_alt, node):

        resp = app.get(f'/v2/nodes/{node._id}/cedar_metadata_records/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_with_read_auth(self, app, node, cedar_record_for_node, cedar_draft_record_for_node):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.get(f'/v2/nodes/{node._id}/cedar_metadata_records/', auth=read.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_node._id in data_set
        assert cedar_draft_record_for_node._id not in data_set

    def test_record_list_with_write_auth(self, app, node, cedar_record_for_node, cedar_draft_record_for_node):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.get(f'/v2/nodes/{node._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_node._id in data_set
        assert cedar_draft_record_for_node._id in data_set

    def test_record_list_with_admin_auth(self, app, node, cedar_record_for_node, cedar_draft_record_for_node):

        admin = AuthUserFactory()
        node.add_contributor(admin, permissions=ADMIN)
        node.save()
        resp = app.get(f'/v2/nodes/{node._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_node._id in data_set
        assert cedar_draft_record_for_node._id in data_set
