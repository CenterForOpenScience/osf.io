import pytest

from .test_registration_cedar_metadata_record import TesRegistrationCedarMetadataRecord
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestRegistrationCedarMetadataRecordList(TesRegistrationCedarMetadataRecord):

    def test_record_list_no_auth(self, app, registration, cedar_record_for_registration, cedar_draft_record_for_registration):
        resp = app.get(f'/v2/registrations/{registration._id}/cedar_metadata_records/')
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_registration._id in data_set
        assert cedar_draft_record_for_registration._id not in data_set

    def test_record_list_with_invalid_auth(self, app, user_alt, registration, cedar_record_for_registration, cedar_draft_record_for_registration):
        resp = app.get(f'/v2/registrations/{registration._id}/cedar_metadata_records/', auth=user_alt.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_registration._id in data_set
        assert cedar_draft_record_for_registration._id not in data_set

    def test_record_list_with_read_auth(self, app, registration, cedar_record_for_registration, cedar_draft_record_for_registration):
        read = AuthUserFactory()
        registration.add_contributor(read, permissions=READ)
        registration.save()
        resp = app.get(f'/v2/registrations/{registration._id}/cedar_metadata_records/', auth=read.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 1
        assert cedar_record_for_registration._id in data_set
        assert cedar_draft_record_for_registration._id not in data_set

    def test_record_list_with_write_auth(self, app, registration, cedar_record_for_registration, cedar_draft_record_for_registration):
        write = AuthUserFactory()
        registration.add_contributor(write, permissions=WRITE)
        registration.save()
        resp = app.get(f'/v2/registrations/{registration._id}/cedar_metadata_records/', auth=write.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_registration._id in data_set
        assert cedar_draft_record_for_registration._id in data_set

    def test_record_list_with_admin_auth(self, app, registration, cedar_record_for_registration, cedar_draft_record_for_registration):
        admin = AuthUserFactory()
        registration.add_contributor(admin, permissions=ADMIN)
        registration.save()
        resp = app.get(f'/v2/registrations/{registration._id}/cedar_metadata_records/', auth=admin.auth)
        assert resp.status_code == 200
        data_set = {datum['id'] for datum in resp.json['data']}
        assert len(data_set) == 2
        assert cedar_record_for_registration._id in data_set
        assert cedar_draft_record_for_registration._id in data_set
