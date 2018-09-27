import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory
)

@pytest.mark.django_db
class TestFileMetadataRecordDownload:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_file(self, user):
        private_node = ProjectFactory(creator=user)
        return utils.create_test_file(private_node, user, filename='private_file')

    @pytest.fixture()
    def private_record(self, user, private_file):
        return private_file.records.first()

    @pytest.fixture()
    def public_file(self, user):
        public_node = ProjectFactory(creator=user, is_public=True)
        return utils.create_test_file(public_node, user, filename='public_file')

    @pytest.fixture()
    def public_record(self, user, public_file):
        return public_file.records.first()

    def get_url(self, record):
        return '/{}files/{}/metadata_records/{}/download/'.format(API_BASE, record.file._id, record._id)

    def test_metadata_record_download(self, app, user, public_record, private_record):

        # test_unauthenticated_can_download_public_file_metadata_record
        res = app.get(self.get_url(public_record))
        assert res.status_code == 200
        assert res.content_type == 'application/json'

        # test_authenticated_can_download_public_file_metadata_record
        res = app.get(self.get_url(public_record), auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/json'

        # test_unauthenticated_cannot_download_private_file_metadata_record
        res = app.get(self.get_url(private_record), expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_download_private_file_metadata_record
        res = app.get(self.get_url(private_record), auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/json'

        # test_unauthorized_cannot_download_private_file_metadata_record
        unauth = AuthUserFactory()
        res = app.get(self.get_url(private_record), auth=unauth.auth, expect_errors=True)
        res.status_code == 403

        # test_can_download_as_xml
        url = self.get_url(public_record) + '?export=xml'
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/xml'

        # test_cannot_download_unknown_format
        url = self.get_url(public_record) + '?export=dinosaur'
        res = app.get(url, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Format "dinosaur" is not supported.'
