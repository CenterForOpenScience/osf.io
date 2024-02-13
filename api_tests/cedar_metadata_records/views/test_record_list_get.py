import pytest

from .test_record import TestCedarMetadataRecord


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
