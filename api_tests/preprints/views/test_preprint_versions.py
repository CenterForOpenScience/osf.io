from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import Field
from django.contrib.auth.models import Group

from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.models import OsfStorageFile
from api.base.settings.defaults import API_BASE

from framework.auth.core import Auth
from osf.models import Preprint
from osf.utils import permissions

from osf_tests.factories import ProjectFactory, PreprintFactory, AuthUserFactory, PreprintProviderFactory
from tests.base import ApiTestCase


class TestPreprintVersionsListCreate(ApiTestCase):

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


class TestPreprintVersionsListRetrieve(ApiTestCase):

    def add_contributors_for_preprint(self, preprint):
        preprint.add_contributor(self.admin, permissions=permissions.ADMIN)
        preprint.add_contributor(self.write_user, permissions=permissions.WRITE)
        preprint.add_contributor(self.read_user, permissions=permissions.READ)

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.read_user = AuthUserFactory()
        self.write_user = AuthUserFactory()
        self.admin = AuthUserFactory()
        osf_admin = Group.objects.get(name='osf_admin')
        self.admin.groups.add(osf_admin)

        self.moderator = AuthUserFactory()
        self.provider = PreprintProviderFactory(_id='osf', name='osfprovider')
        self.post_mod_preprint = PreprintFactory(
            reviews_workflow='post-moderation',
            is_published=True,
            creator=self.user,
            provider=self.provider
        )

        self.pre_mod_preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False,
            creator=self.user,
            provider=self.provider
        )
        self.add_contributors_for_preprint(self.pre_mod_preprint)

        self.pre_mod_preprint_pending = PreprintFactory(
            reviews_workflow='pre-moderation',
            is_published=False,
            creator=self.user,
            provider=self.provider
        )
        self.add_contributors_for_preprint(self.pre_mod_preprint_pending)
        self.pre_mod_preprint_pending.run_submit(user=self.admin)
        self.pre_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        self.post_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        self.latest_preprint = self.post_mod_preprint
        self.origin_guid = str(self.post_mod_preprint.guids.first()._id)
        for _ in range(5):
            new_version = PreprintFactory.create_version(
                create_from=self.latest_preprint,
                creator=self.user,
                set_doi=False
            )
            self.latest_preprint = new_version

        self.version_list_url = f"/{API_BASE}preprints/{self.origin_guid}_v1/versions/"

    def test_list_versions(self):
        res = self.app.get(self.version_list_url, auth=self.user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 6
        assert len(set([item['id'] for item in data])) == 6

    def test_public_visibility(self):
        self.pre_mod_preprint.is_public = True
        self.pre_mod_preprint.save()
        res = self.app.get(self.version_list_url)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

    def test_invalid_preprint_id(self):
        res = self.app.get(f"/{API_BASE}preprints/lkziv_v1010101/versions/", auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_pagination(self):
        res = self.app.get(f"{self.version_list_url}?page[size]=2", auth=self.user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert 'links' in res.json
        assert 'next' in res.json['links']

    def test_new_unpublished_version(self):
        PreprintFactory.create_version(
            self.latest_preprint,
            creator=self.user,
            set_doi=False,
            final_machine_state='pending',
            is_published=False
        )
        res = self.app.get(self.version_list_url, auth=self.user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 7
        assert len(set([item['id'] for item in data])) == 7

    def test_preprints_version_permissions_for_admin(self):
        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        self.latest_preprint = unpublished_preprint_version
        unpublished_preprint_version.add_contributor(self.admin, permissions=permissions.ADMIN)

        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_preprint_version.run_submit(user=self.admin)
        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_preprint_version.run_accept(user=self.admin, comment='Text')

        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        unpublished_version.add_contributor(self.admin, permissions=permissions.ADMIN)

        unpublished_version.run_submit(user=self.admin)

        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 8

        unpublished_version.run_reject(user=self.admin, comment='Test')
        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 8

    def test_preprints_version_permissions_for_write_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        self.latest_preprint = unpublished_preprint_version
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_submit(user=self.admin)
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_accept(user=self.admin, comment='Text')

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )

        unpublished_version.run_submit(user=self.admin)

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version.run_reject(user=self.admin, comment='Test')
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_pre_mod_preprints_version_permissions_for_read_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        self.latest_preprint = unpublished_preprint_version
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_submit(user=self.admin)
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_accept(user=self.admin, comment='Text')

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )

        unpublished_version.run_submit(user=self.admin)

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version.run_reject(user=self.admin, comment='Test')
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_pre_mod_preprints_version_permissions_for_other_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        self.latest_preprint = unpublished_preprint_version
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_submit(user=self.admin)
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        unpublished_preprint_version.run_accept(user=self.admin, comment='Text')

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version = PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )

        unpublished_version.run_submit(user=self.admin)

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

        unpublished_version.run_reject(user=self.admin, comment='Test')
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_post_mod_preprints_version_permissions_for_admin_user(self):
        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='accepted',
            is_published=True,
            set_doi=False
        )
        res = self.app.get(self.version_list_url, auth=self.admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_post_mod_preprints_version_permissions_for_write_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='accepted',
            is_published=True,
            set_doi=False
        )

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_post_mod_preprints_version_permissions_for_read_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='accepted',
            is_published=True,
            set_doi=False
        )

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7

    def test_post_mod_preprints_version_permissions_for_other_user(self):
        new_user = AuthUserFactory()
        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 6

        PreprintFactory.create_version(
            create_from=self.latest_preprint,
            creator=self.user,
            final_machine_state='accepted',
            is_published=True,
            set_doi=False
        )

        res = self.app.get(self.version_list_url, auth=new_user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 7
