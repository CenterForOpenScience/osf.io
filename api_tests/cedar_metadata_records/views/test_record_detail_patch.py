import pytest

from .test_record import TestCedarMetadataRecord
from osf.utils.permissions import READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestCedarMetadataRecordDetailUpdateForProjects(TestCedarMetadataRecord):
    def test_record_detail_update_for_node_with_admin_auth(
        self,
        app,
        user,
        payload_record_update,
        cedar_record_for_node,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert cedar_record_for_node.metadata == cedar_record_metadata_json
        assert cedar_record_for_node.is_published

        admin = user
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            payload_record_update,
            auth=admin.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_node._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_node.reload()
        assert cedar_record_for_node.metadata == cedar_record_metadata_alt_json
        assert not cedar_record_for_node.is_published

    def test_record_detail_update_for_node_with_write_auth(
        self,
        app,
        node,
        payload_record_update,
        cedar_record_for_node,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert cedar_record_for_node.metadata == cedar_record_metadata_json
        assert cedar_record_for_node.is_published

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            payload_record_update,
            auth=write.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_node._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_node.reload()
        assert cedar_record_for_node.metadata == cedar_record_metadata_alt_json
        assert not cedar_record_for_node.is_published

    def test_record_detail_update_for_node_with_read_auth(
        self, app, node, payload_record_update, cedar_record_for_node
    ):
        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            payload_record_update,
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_node_with_invalid_auth(
        self, app, user_alt, payload_record_update, cedar_record_for_node
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            payload_record_update,
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_node_with_no_auth(
        self, app, payload_record_update, cedar_record_for_node
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            payload_record_update,
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordDetailUpdateForRegistrations(
    TestCedarMetadataRecord
):
    def test_record_detail_update_for_registration_with_admin_auth(
        self,
        app,
        user,
        payload_record_update,
        cedar_record_for_registration,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert (
            cedar_record_for_registration.metadata
            == cedar_record_metadata_json
        )
        assert cedar_record_for_registration.is_published

        admin = user
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            payload_record_update,
            auth=admin.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_registration._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_registration.reload()
        assert (
            cedar_record_for_registration.metadata
            == cedar_record_metadata_alt_json
        )
        assert not cedar_record_for_registration.is_published

    def test_record_detail_update_for_registration_with_write_auth(
        self,
        app,
        registration,
        payload_record_update,
        cedar_record_for_registration,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert (
            cedar_record_for_registration.metadata
            == cedar_record_metadata_json
        )
        assert cedar_record_for_registration.is_published

        write = AuthUserFactory()
        registration.add_contributor(write, permissions=WRITE)
        registration.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            payload_record_update,
            auth=write.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_registration._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_registration.reload()
        assert (
            cedar_record_for_registration.metadata
            == cedar_record_metadata_alt_json
        )
        assert not cedar_record_for_registration.is_published

    def test_record_detail_update_for_registration_with_read_auth(
        self,
        app,
        registration,
        payload_record_update,
        cedar_record_for_registration,
    ):
        read = AuthUserFactory()
        registration.add_contributor(read, permissions=READ)
        registration.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            payload_record_update,
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_registration_with_invalid_auth(
        self,
        app,
        user_alt,
        payload_record_update,
        cedar_record_for_registration,
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            payload_record_update,
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_registration_with_no_auth(
        self, app, payload_record_update, cedar_record_for_registration
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            payload_record_update,
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordDetailUpdateForFiles(TestCedarMetadataRecord):
    def test_record_detail_update_for_file_with_admin_auth(
        self,
        app,
        user,
        payload_record_update,
        cedar_record_for_file,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert cedar_record_for_file.metadata == cedar_record_metadata_json
        assert cedar_record_for_file.is_published

        admin = user
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            payload_record_update,
            auth=admin.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_file._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_file.reload()
        assert cedar_record_for_file.metadata == cedar_record_metadata_alt_json
        assert not cedar_record_for_file.is_published

    def test_record_detail_update_for_file_with_write_auth(
        self,
        app,
        node,
        payload_record_update,
        cedar_record_for_file,
        cedar_record_metadata_json,
        cedar_record_metadata_alt_json,
    ):
        assert cedar_record_for_file.metadata == cedar_record_metadata_json
        assert cedar_record_for_file.is_published

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            payload_record_update,
            auth=write.auth,
        )
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == cedar_record_for_file._id
        assert data["type"] == "cedar-metadata-records"

        cedar_record_for_file.reload()
        assert cedar_record_for_file.metadata == cedar_record_metadata_alt_json
        assert not cedar_record_for_file.is_published

    def test_record_detail_update_for_file_with_read_auth(
        self, app, node, payload_record_update, cedar_record_for_file
    ):
        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            payload_record_update,
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_file_with_invalid_auth(
        self, app, user_alt, payload_record_update, cedar_record_for_file
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            payload_record_update,
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_update_for_file_with_no_auth(
        self, app, payload_record_update, cedar_record_for_file
    ):
        resp = app.patch_json(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            payload_record_update,
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401
