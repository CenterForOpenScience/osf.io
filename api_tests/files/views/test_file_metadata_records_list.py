import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
)


@pytest.mark.django_db
class TestFileMetadataRecordsList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_file(self, user):
        private_node = ProjectFactory(creator=user)
        return utils.create_test_file(private_node, user, filename='private_file')

    @pytest.fixture()
    def public_file(self, user):
        public_node = ProjectFactory(creator=user, is_public=True)
        return utils.create_test_file(public_node, user, filename='public_file')

    def get_url(self, file):
        return '/{}files/{}/metadata_records/'.format(API_BASE, file._id)

    def test_metadata_record_list(self, app, user, public_file, private_file):

        # test_unauthenticated_can_view_public_file_metadata_records
        res = app.get(self.get_url(public_file))
        assert res.status_code == 200
        assert len(res.json['data']) == public_file.records.count()

        # test_authenticated_can_view_public_file_metadata_records
        res = app.get(self.get_url(public_file), auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_file.records.count()

        # test_unauthenticated_cannot_view_private_file_metadata_records
        res = app.get(self.get_url(private_file), expect_errors=True)
        assert res.status_code == 401

        # test_authenticated_can_view_private_file_metadata_records
        res = app.get(self.get_url(private_file), auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == private_file.records.count()

        # test_unauthorized_cannot_view_private_file_metadata_records
        unauth = AuthUserFactory()
        res = app.get(self.get_url(private_file), auth=unauth.auth, expect_errors=True)
        assert res.status_code == 403

        # test_cannot_create_metadata_records
        res = app.post_json_api(self.get_url(private_file), auth=user.auth, expect_errors=True)
        assert res.status_code == 405
