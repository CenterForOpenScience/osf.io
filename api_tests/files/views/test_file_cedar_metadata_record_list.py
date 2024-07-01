import pytest

from .test_file_cedar_metdata_record import TestFileCedarMetadataRecord
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestFileCedarMetadataRecordListPublicFile(TestFileCedarMetadataRecord):

    def test_record_list_no_auth(self, app, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        resp = app.get(f'/v2/files/{file_pub._id}/cedar_metadata_records/')
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id not in data_set

    def test_record_list_with_invalid_auth(self, app, user_alt, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        resp = app.get(f'/v2/files/{file_pub._id}/cedar_metadata_records/', auth=user_alt.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id not in data_set

    def test_record_list_with_read_auth(self, app, node_pub, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        read = AuthUserFactory()
        node_pub.add_contributor(read, permissions=READ)
        node_pub.save()
        resp = app.get(f'/v2/files/{file_pub._id}/cedar_metadata_records/', auth=read.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id not in data_set

    def test_record_list_with_write_auth(self, app, node_pub, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        write = AuthUserFactory()
        node_pub.add_contributor(write, permissions=WRITE)
        node_pub.save()
        resp = app.get(f'/v2/files/{file_pub._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id in data_set

    def test_record_list_with_admin_auth(self, app, node_pub, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        admin = AuthUserFactory()
        node_pub.add_contributor(admin, permissions=ADMIN)
        node_pub.save()
        resp = app.get(f'/v2/files/{file_pub._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id in data_set


@pytest.mark.django_db
class TestFileCedarMetadataRecordListPrivateFile(TestFileCedarMetadataRecord):

    def test_record_list_no_auth(self, app, file):

        resp = app.get(f'/v2/files/{file._id}/cedar_metadata_records/', expect_errors=True)
        assert resp.status_code == 401

    def test_record_list_with_invalid_auth(self, app, user_alt, file):

        resp = app.get(f'/v2/files/{file._id}/cedar_metadata_records/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_list_with_read_auth(self, app, node, file, cedar_record_for_file, cedar_draft_record_for_file):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.get(f'/v2/files/{file._id}/cedar_metadata_records/', auth=read.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_file._id in data_set
        assert cedar_draft_record_for_file._id not in data_set

    def test_record_list_with_write_auth(self, app, node, file, cedar_record_for_file, cedar_draft_record_for_file):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.get(f'/v2/files/{file._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file._id in data_set
        assert cedar_draft_record_for_file._id in data_set

    def test_record_list_with_admin_auth(self, app, node, file, cedar_record_for_file, cedar_draft_record_for_file):

        admin = AuthUserFactory()
        node.add_contributor(admin, permissions=ADMIN)
        node.save()
        resp = app.get(f'/v2/files/{file._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file._id in data_set
        assert cedar_draft_record_for_file._id in data_set


@pytest.mark.django_db
class TestFileCedarMetadataRecordListFileWithGuid(TestFileCedarMetadataRecord):

    def test_private_file_record_list_with_admin_auth(self, app, node, file, cedar_record_for_file, cedar_draft_record_for_file):

        file_guid = file.get_guid(create=False)
        admin = AuthUserFactory()
        node.add_contributor(admin, permissions=ADMIN)
        node.save()
        resp = app.get(f'/v2/files/{file_guid._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file._id in data_set
        assert cedar_draft_record_for_file._id in data_set

    def test_public_file_record_list_with_write_auth(self, app, node_pub, file_pub, cedar_record_for_file_pub, cedar_draft_record_for_file_pub):

        file_guid = file_pub.get_guid(create=False)
        write = AuthUserFactory()
        node_pub.add_contributor(write, permissions=WRITE)
        node_pub.save()
        resp = app.get(f'/v2/files/{file_guid._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_file_pub._id in data_set
        assert cedar_draft_record_for_file_pub._id in data_set
