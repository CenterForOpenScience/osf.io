import pytest

from .test_record import TestCedarMetadataRecord
from osf.models import CedarMetadataRecord
from osf.utils.permissions import READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestCedarMetadataRecordDetailDeleteForProjects(TestCedarMetadataRecord):
    def test_record_detail_delete_for_node_with_admin_auth(
        self, app, user, cedar_record_for_node
    ):
        assert cedar_record_for_node is not None
        record_id = cedar_record_for_node._id

        admin = user
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            auth=admin.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_node_with_write_auth(
        self, app, node, cedar_record_for_node
    ):
        assert cedar_record_for_node is not None
        record_id = cedar_record_for_node._id

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            auth=write.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_node_with_read_auth(
        self, app, node, cedar_record_for_node
    ):
        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()

        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_node_with_invalid_auth(
        self, app, user_alt, cedar_record_for_node
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_node_with_no_auth(
        self, app, cedar_record_for_node
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_node._id}/",
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordDetailDeleteForRegistrations(
    TestCedarMetadataRecord
):
    def test_record_detail_delete_for_registration_with_admin_auth(
        self, app, user, cedar_record_for_registration
    ):
        assert cedar_record_for_registration is not None
        record_id = cedar_record_for_registration._id

        admin = user
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            auth=admin.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_registration_with_write_auth(
        self, app, registration, cedar_record_for_registration
    ):
        assert cedar_record_for_registration is not None
        record_id = cedar_record_for_registration._id

        write = AuthUserFactory()
        registration.add_contributor(write, permissions=WRITE)
        registration.save()
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            auth=write.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_registration_with_read_auth(
        self, app, registration, cedar_record_for_registration
    ):
        read = AuthUserFactory()
        registration.add_contributor(read, permissions=READ)
        registration.save()

        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_registration_with_invalid_auth(
        self, app, user_alt, cedar_record_for_registration
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_registration_with_no_auth(
        self, app, cedar_record_for_registration
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_registration._id}/",
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordDetailDeleteForFiles(TestCedarMetadataRecord):
    def test_record_detail_delete_for_file_with_admin_auth(
        self, app, user, cedar_record_for_file
    ):
        assert cedar_record_for_file is not None
        record_id = cedar_record_for_file._id

        admin = user
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            auth=admin.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_file_with_write_auth(
        self, app, node, cedar_record_for_file
    ):
        assert cedar_record_for_file is not None
        record_id = cedar_record_for_file._id

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            auth=write.auth,
        )
        assert resp.status_code == 204

        with pytest.raises(CedarMetadataRecord.DoesNotExist):
            CedarMetadataRecord.objects.get(_id=record_id)

    def test_record_detail_delete_for_file_with_read_auth(
        self, app, node, cedar_record_for_file
    ):
        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()

        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            auth=read.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_file_with_invalid_auth(
        self, app, user_alt, cedar_record_for_file
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            auth=user_alt.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    def test_record_detail_delete_for_file_with_no_auth(
        self, app, cedar_record_for_file
    ):
        resp = app.delete(
            f"/_/cedar_metadata_records/{cedar_record_for_file._id}/",
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401
