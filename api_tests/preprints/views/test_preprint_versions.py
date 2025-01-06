from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import Field

from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.models import OsfStorageFile
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import Preprint
from osf.utils import permissions
from osf_tests.factories import ProjectFactory, PreprintFactory, AuthUserFactory
from tests.base import ApiTestCase


# TODO: we have good coverage for `POST`; please add new tests for `GET`
class TestPreprintVersion(ApiTestCase):

    def setUp(self):

        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.moderator = AuthUserFactory()
        self.post_mod_preprint = PreprintFactory(
            reviews_workflow='post-moderation',
            is_published=True,
            creator=self.user
        )
        self.pre_mod_preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False,
            creator=self.user
        )
        self.post_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        self.pre_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        self.post_mod_version_create_url = f'/{API_BASE}preprints/{self.post_mod_preprint._id}/versions/?version=2.20'
        self.pre_mode_version_create_url = f'/{API_BASE}preprints/{self.pre_mod_preprint._id}/versions/?version=2.20'
        self.post_mod_preprint_update_url = f'/{API_BASE}preprints/{self.post_mod_preprint._id}/?version=2.20'
        self.post_mod_preprint_update_payload = {
            'data': {
                'id': self.post_mod_preprint._id,
                'type': 'preprints',
                'attributes': {
                    'title': 'new_title',
                }
            }
        }

    def test_create_preprint_version(self):
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        assert res.status_code == 201
        new_version = Preprint.load(res.json['data']['id'])
        assert new_version.is_published is False
        assert new_version.machine_state == 'initial'
        assert new_version.files.count() == 0

    def test_non_relation_fields(self):
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        ignored_fields = [
            'id', 'created', 'modified', 'last_logged', 'date_last_reported', 'reports', 'date_last_transitioned',
            'machine_state', 'is_published', 'date_published', 'preprint_doi_created', 'ever_public', 'has_coi'
        ]
        new_version = Preprint.load(res.json['data']['id'])
        non_relation_fields = [
            field.name for field in self.post_mod_preprint._meta.get_fields()
            if isinstance(field, Field) and
            not field.is_relation and
            field.name not in ignored_fields
        ]
        preprint_data = {field: getattr(self.post_mod_preprint, field) for field in non_relation_fields}
        preprint_version_data = {field: getattr(new_version, field) for field in non_relation_fields}
        assert preprint_data == preprint_version_data

    def test_relation_fields(self):
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        new_version = Preprint.load(res.json['data']['id'])
        assert self.post_mod_preprint.provider == new_version.provider
        assert self.post_mod_preprint.node == new_version.node
        assert self.post_mod_preprint.license == new_version.license
        assert self.post_mod_preprint.creator == new_version.creator
        assert self.post_mod_preprint.region == new_version.region
        assert list(self.post_mod_preprint.tags.values_list('name', flat=True)) == list(new_version.tags.values_list('name', flat=True))
        assert list(self.post_mod_preprint.subjects.values_list('text', flat=True)) == list(new_version.subjects.values_list('text', flat=True))
        assert list(self.post_mod_preprint.affiliated_institutions.values_list('name', flat=True)) == list(new_version.affiliated_institutions.values_list('name', flat=True))
        assert list(self.post_mod_preprint._contributors.values_list('username', flat=True)) == list(new_version._contributors.values_list('username', flat=True))

    def test_return_409_if_unpublished_pending_version_exists(self):
        res = self.app.post_json_api(self.pre_mode_version_create_url, auth=self.user.auth)
        new_version = Preprint.load(res.json['data']['id'])
        filename = 'preprint_file.txt'
        preprint_file = OsfStorageFile.create(
            target_object_id=new_version.id,
            target_content_type=ContentType.objects.get_for_model(new_version),
            path=f'/{filename}',
            name=filename,
            materialized_path=f'/{filename}'
        )
        preprint_file.save()
        new_version.set_primary_file(preprint_file, auth=Auth(new_version.creator), save=True)
        location = {'object': '06d80e', 'service': 'cloud', osfstorage_settings.WATERBUTLER_RESOURCE: 'osf', }
        metadata = {'size': 1357, 'contentType': 'img/png', }
        preprint_file.create_version(self.user, location, metadata=metadata).save()
        new_version.run_submit(self.moderator)
        assert new_version.is_published is False
        assert new_version.machine_state == 'pending'
        res = self.app.post_json_api(self.pre_mode_version_create_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 409

    def test_return_409_if_try_to_edit_old_versions(self):
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        new_version = Preprint.load(res.json['data']['id'])
        filename = 'preprint_file.txt'
        preprint_file = OsfStorageFile.create(
            target_object_id=new_version.id,
            target_content_type=ContentType.objects.get_for_model(new_version),
            path=f'/{filename}',
            name=filename,
            materialized_path=f'/{filename}'
        )
        preprint_file.save()
        new_version.set_primary_file(preprint_file, auth=Auth(new_version.creator), save=True)
        location = {'object': '06d80e', 'service': 'cloud', osfstorage_settings.WATERBUTLER_RESOURCE: 'osf', }
        metadata = {'size': 1357, 'contentType': 'img/png', }
        preprint_file.create_version(self.user, location, metadata=metadata).save()
        new_version.run_submit(self.moderator)
        assert new_version.is_published is True
        new_version.run_accept(self.moderator, 'comment')
        assert new_version.machine_state == 'accepted'
        res = self.app.patch_json_api(
            self.post_mod_preprint_update_url,
            self.post_mod_preprint_update_payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_reuse_version_if_unfinished_version_exists(self):
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        unfinished_version = Preprint.load(res.json['data']['id'])
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 201
        assert res.json['data']['id'] == unfinished_version._id

    def test_permission_error(self):
        # No auth returns 401
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=None, expect_errors=True)
        assert res.status_code == 401
        # READ returns 403
        user_read = AuthUserFactory()
        self.post_mod_preprint.add_contributor(user_read, permissions.READ)
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=user_read.auth, expect_errors=True)
        assert res.status_code == 403
        # WRITE returns 403
        user_write = AuthUserFactory()
        self.post_mod_preprint.add_contributor(user_write, permissions.WRITE)
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=user_write.auth, expect_errors=True)
        assert res.status_code == 403
