import pytest

from .test_record import TestCedarMetadataRecord
from osf.utils.permissions import READ, WRITE
from osf_tests.factories import AuthUserFactory

@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPrivateProjectPublishedMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, node, user, cedar_record_for_node, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node, cedar_record_for_node, cedar_record_metadata_json):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node, cedar_record_for_node, cedar_record_metadata_json):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node._id}/metadata_download/', auth=read.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_record_for_node):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_record_for_node):
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPrivateProjectDraftMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_draft_record_for_node_alt, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_alt._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_node_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_alt, cedar_draft_record_for_node_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_alt.add_contributor(write, permissions=WRITE)
        node_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_alt._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_node_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_alt, cedar_draft_record_for_node_alt):

        read = AuthUserFactory()
        node_alt.add_contributor(read, permissions=READ)
        node_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_alt._id}/metadata_download/', auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_draft_record_for_node_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_alt._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_draft_record_for_node_alt):
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_alt._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPublicProjectPublishedMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_record_for_node_pub, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node_pub._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_pub.add_contributor(write, permissions=WRITE)
        node_pub.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node_pub._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_pub, cedar_record_for_node_pub, cedar_record_metadata_json):

        read = AuthUserFactory()
        node_pub.add_contributor(read, permissions=READ, notification_type=False)
        node_pub.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node_pub._id}/metadata_download/', auth=read.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_record_for_node_pub, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node_pub._id}/metadata_download/', auth=user_alt.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_record_for_node_pub, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_node_pub._id}/metadata_download/', auth=None)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_node_pub)}'
        assert resp.json == cedar_record_metadata_json


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPublicProjectDraftMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_draft_record_for_node_pub_alt, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_pub_alt._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_node_pub_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_pub_alt, cedar_draft_record_for_node_pub_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_pub_alt.add_contributor(write, permissions=WRITE)
        node_pub_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_pub_alt._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_node_pub_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_pub_alt, cedar_draft_record_for_node_pub_alt):

        read = AuthUserFactory()
        node_pub_alt.add_contributor(read, permissions=READ)
        node_pub_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_pub_alt._id}/metadata_download/', auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_draft_record_for_node_pub_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_pub_alt._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_draft_record_for_node_pub_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_node_pub_alt._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadRegistrationPublishedMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_registration_with_admin_auth(self, app, user, cedar_record_for_registration, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_registration._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_registration)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_write_auth(self, app, registration, cedar_record_for_registration, cedar_record_metadata_json):

        write = AuthUserFactory()
        registration.add_contributor(write, permissions=WRITE)
        registration.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_registration._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_registration)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_read_auth(self, app, registration, cedar_record_for_registration, cedar_record_metadata_json):

        read = AuthUserFactory()
        registration.add_contributor(read, permissions=READ)
        registration.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_registration._id}/metadata_download/', auth=read.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_registration)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_invalid_auth(self, app, user_alt, cedar_record_for_registration, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_registration._id}/metadata_download/', auth=user_alt.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_registration)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_no_auth(self, app, cedar_record_for_registration, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_registration._id}/metadata_download/', auth=None)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_registration)}'
        assert resp.json == cedar_record_metadata_json


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadRegistrationDraftMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_registration_with_admin_auth(self, app, user, cedar_draft_record_for_registration_alt, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_registration_alt._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_registration_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_write_auth(self, app, registration_alt, cedar_draft_record_for_registration_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        registration_alt.add_contributor(write, permissions=WRITE)
        registration_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_registration_alt._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_registration_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_registration_with_read_auth(self, app, registration_alt, cedar_draft_record_for_registration_alt):

        read = AuthUserFactory()
        registration_alt.add_contributor(read, permissions=READ)
        registration_alt.save()

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_registration_alt._id}/metadata_download/', auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_registration_with_invalid_auth(self, app, user_alt, cedar_draft_record_for_registration_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_registration_alt._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_registration_with_no_auth(self, app, cedar_draft_record_for_registration_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_registration_alt._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPrivateFilePublishedMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_record_for_file, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node, cedar_record_for_file, cedar_record_metadata_json):

        write = AuthUserFactory()
        node.add_contributor(write, permissions=WRITE)
        node.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node, cedar_record_for_file, cedar_record_metadata_json):

        read = AuthUserFactory()
        node.add_contributor(read, permissions=READ)
        node.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file._id}/metadata_download/', auth=read.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_record_for_file):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_record_for_file):
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPrivateFileDraftMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_draft_record_for_file_alt, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_alt._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_file_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_alt, cedar_draft_record_for_file_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_alt.add_contributor(write, permissions=WRITE)
        node_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_alt._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_file_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_alt, cedar_draft_record_for_file_alt):

        read = AuthUserFactory()
        node_alt.add_contributor(read, permissions=READ)
        node_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_alt._id}/metadata_download/', auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_draft_record_for_file_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_alt._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_draft_record_for_file_alt):
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_alt._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPublicFilePublishedMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_record_for_file_pub, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file_pub._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_pub, cedar_record_for_file_pub, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_pub.add_contributor(write, permissions=WRITE)
        node_pub.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file_pub._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_pub, cedar_record_for_file_pub, cedar_record_metadata_json):

        read = AuthUserFactory()
        node_pub.add_contributor(read, permissions=READ, notification_type=False)
        node_pub.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file_pub._id}/metadata_download/', auth=read.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_record_for_file_pub, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file_pub._id}/metadata_download/', auth=user_alt.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file_pub)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_record_for_file_pub, cedar_record_metadata_json):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_record_for_file_pub._id}/metadata_download/', auth=None)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_record_for_file_pub)}'
        assert resp.json == cedar_record_metadata_json


@pytest.mark.django_db
class TestCedarMetadataRecordMetadataDownloadPublicFileDraftMetadata(TestCedarMetadataRecord):

    def test_record_metadata_download_for_node_with_admin_auth(self, app, user, cedar_draft_record_for_file_pub_alt, cedar_record_metadata_json):

        admin = user
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_pub_alt._id}/metadata_download/', auth=admin.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_file_pub_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_write_auth(self, app, node_pub_alt, cedar_draft_record_for_file_pub_alt, cedar_record_metadata_json):

        write = AuthUserFactory()
        node_pub_alt.add_contributor(write, permissions=WRITE)
        node_pub_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_pub_alt._id}/metadata_download/', auth=write.auth)
        assert resp.status_code == 200
        assert resp.headers['Content-Disposition'] == f'attachment; filename={self.get_record_metadata_download_file_name(cedar_draft_record_for_file_pub_alt)}'
        assert resp.json == cedar_record_metadata_json

    def test_record_metadata_download_for_node_with_read_auth(self, app, node_pub_alt, cedar_draft_record_for_file_pub_alt):

        read = AuthUserFactory()
        node_pub_alt.add_contributor(read, permissions=READ)
        node_pub_alt.save()
        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_pub_alt._id}/metadata_download/', auth=read.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_invalid_auth(self, app, user_alt, cedar_draft_record_for_file_pub_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_pub_alt._id}/metadata_download/', auth=user_alt.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_record_metadata_download_for_node_with_no_auth(self, app, cedar_draft_record_for_file_pub_alt):

        resp = app.get(f'/_/cedar_metadata_records/{cedar_draft_record_for_file_pub_alt._id}/metadata_download/', auth=None, expect_errors=True)
        assert resp.status_code == 401
