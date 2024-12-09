from api.base.settings.defaults import API_BASE
from osf.models import Preprint
from osf.utils import permissions
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
)
from tests.base import ApiTestCase

from django.db.models.fields import Field


class TestPreprintVersion(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user)

        self.project = ProjectFactory(creator=self.user)

        self.url = f'/{API_BASE}preprints/{self.preprint._id}/versions/'

    def test_create_preprint_version(self):
        res = self.app.post_json_api(self.url, auth=self.user.auth)

        assert res.status_code == 201

    def test_non_relation_fields(self):
        res = self.app.post_json_api(self.url, auth=self.user.auth)

        # TODO
        ignored_fields = [
            'id', 'created', 'modified', 'last_logged', 'date_last_reported',
            'reports', 'date_last_transitioned', 'machine_state', 'is_published',
            'date_published', 'preprint_doi_created', 'ever_public', 'has_coi']

        preprint_version = Preprint.load(res.json['data']['id'])
        non_relation_fields = [
            field.name for field in self.preprint._meta.get_fields()
            if isinstance(field, Field) and
            not field.is_relation and
            field.name not in ignored_fields
        ]
        preprint_data = {field: getattr(self.preprint, field) for field in non_relation_fields}
        preprint_version_data = {field: getattr(preprint_version, field) for field in non_relation_fields}
        assert preprint_data == preprint_version_data

    def test_relation_fields(self):
        res = self.app.post_json_api(self.url, auth=self.user.auth)

        preprint_version = Preprint.load(res.json['data']['id'])

        # TODO
        assert self.preprint.provider == preprint_version.provider
        assert self.preprint.node == preprint_version.node
        assert self.preprint.license == preprint_version.license
        assert self.preprint.creator == preprint_version.creator
        assert self.preprint.region == preprint_version.region
        assert list(self.preprint.tags.values_list('name', flat=True)) == list(preprint_version.tags.values_list('name', flat=True))
        assert list(self.preprint.subjects.values_list('text', flat=True)) == list(preprint_version.subjects.values_list('text', flat=True))
        assert list(self.preprint.affiliated_institutions.values_list('name', flat=True)) == list(preprint_version.affiliated_institutions.values_list('name', flat=True))
        assert list(self.preprint._contributors.values_list('username', flat=True)) == list(preprint_version._contributors.values_list('username', flat=True))

    def test_pending_version_exists(self):
        self.app.post_json_api(self.url, auth=self.user.auth)
        res = self.app.post_json_api(self.url, auth=self.user.auth, expect_errors=True)

        assert res.status_code == 409

    def test_permission_error(self):
        user_read = AuthUserFactory()
        self.preprint.add_contributor(user_read, permissions.READ)
        res = self.app.post_json_api(self.url, auth=user_read.auth, expect_errors=True)

        assert res.status_code == 403
