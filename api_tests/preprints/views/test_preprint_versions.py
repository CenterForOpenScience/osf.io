from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import Field
from django.utils import timezone

from addons.osfstorage import settings as osfstorage_settings
from addons.osfstorage.models import OsfStorageFile
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import Preprint
from osf.utils import permissions
from osf.utils.workflows import DefaultStates, RequestTypes
from osf_tests.factories import ProjectFactory, PreprintFactory, AuthUserFactory, PreprintRequestFactory
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

    def test_preprint_version_inherits_contributors_ordering_from_original(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        user3 = AuthUserFactory()
        self.post_mod_preprint.add_contributor(user1)
        self.post_mod_preprint.add_contributor(user2)
        self.post_mod_preprint.add_contributor(user3)

        # create a new version
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        assert res.status_code == 201

        url = f'/{API_BASE}preprints/{self.post_mod_preprint._id}/contributors/'
        contributors_res = self.app.get(url, auth=self.user.auth)
        contributors = contributors_res.json['data']
        # creator always becomes the first contributor in original preprint, then other contributors one by one
        correct_contributors_ordering = [self.user, user1, user2, user3]
        for returned_contributor, correct_contributor in list(zip(contributors, correct_contributors_ordering)):
            returned_contributor_id = returned_contributor['embeds']['users']['data']['id']
            assert returned_contributor_id == correct_contributor._id

    def test_preprint_version_inherits_changed_contributors_ordering_from_previous_version(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        user3 = AuthUserFactory()
        self.post_mod_preprint.add_contributor(user1)
        self.post_mod_preprint.add_contributor(user2)
        self.post_mod_preprint.add_contributor(user3)

        # create a new version
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        assert res.status_code == 201

        # ordering should become: user3, creator, user2, user1
        contributor_id = f'{self.post_mod_preprint._id}-{user3._id}'
        url = f'/{API_BASE}preprints/{self.post_mod_preprint._id}/contributors/{user3._id}/'
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 0
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user.auth, expect_errors=True)
        assert res_patch.status_code == 200

        # publish the latest version because Preprint.create_version will return an unfinished version
        auth = Auth(user=self.user)
        latest_version = self.post_mod_preprint.get_last_not_rejected_version()
        latest_version.date_published = timezone.now()
        latest_version.save()

        new_version_v3, _ = Preprint.create_version(latest_version._id, auth)
        assert new_version_v3._id != latest_version._id

        url = f'/{API_BASE}preprints/{new_version_v3._id}/contributors/'
        contributors = self.app.get(url, auth=self.user.auth).json['data']
        correct_contributors_ordering = [user3, self.user, user1, user2]
        for returned_contributor, correct_contributor in list(zip(contributors, correct_contributors_ordering)):
            returned_contributor_id = returned_contributor['embeds']['users']['data']['id']
            assert returned_contributor_id == correct_contributor._id

    def test_preprint_version_inherits_new_contributors_from_previous_version(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        user3 = AuthUserFactory()
        self.post_mod_preprint.add_contributor(user1)
        self.post_mod_preprint.add_contributor(user2)
        self.post_mod_preprint.add_contributor(user3)

        # create a new version
        res = self.app.post_json_api(self.post_mod_version_create_url, auth=self.user.auth)
        assert res.status_code == 201

        new_contributor = AuthUserFactory()
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': new_contributor._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        new_version_id = res.json['data']['id']
        url = f'/{API_BASE}preprints/{new_version_id}/contributors/'

        res = self.app.post_json_api(url, data, auth=self.user.auth)
        assert res.status_code == 201

        # publish the latest version because Preprint.create_version will return an unfinished version
        auth = Auth(user=self.user)
        latest_version = self.post_mod_preprint.get_last_not_rejected_version()
        latest_version.date_published = timezone.now()
        latest_version.save()

        new_version_v3, _ = Preprint.create_version(latest_version._id, auth)
        assert new_version_v3._id != latest_version._id

        url = f'/{API_BASE}preprints/{new_version_v3._id}/contributors/'
        contributors = self.app.get(url, auth=self.user.auth).json['data']
        correct_contributors_ordering = [self.user, user1, user2, user3, new_contributor]
        for returned_contributor, correct_contributor in list(zip(contributors, correct_contributors_ordering)):
            returned_contributor_id = returned_contributor['embeds']['users']['data']['id']
            assert returned_contributor_id == correct_contributor._id

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

    def test_incorrect_preprint_id_without_version_returns_404(self):
        res = self.app.get(f'/{API_BASE}preprints/1234/', auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_not_approved_preprint_in_pre_moderation_is_shown_for_contributors_only(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]
        preprint_version_id = self.pre_mod_preprint._id

        # unapproved original preprint is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'initial'

        # unapproved preprint version is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_version_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'initial'

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)

        # unapproved original preprint is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'initial'

        # unapproved preprint version is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_version_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'initial'

        random_user = AuthUserFactory()
        # unapproved original preprint is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

        # unapproved preprint version is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_version_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_pending_preprint_in_pre_moderation_is_shown_for_contributors_only(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)

        # pending original preprint is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'pending'

        # pending preprint version is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.json['data']['attributes']['reviews_state'] == 'pending'
        assert res.status_code == 200

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)

        # pending original preprint is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'pending'

        # pending preprint version is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'pending'

        random_user = AuthUserFactory()
        # pending original preprint is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

        # pending preprint version is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_pending_preprint_in_pre_moderation_withdrawn_is_shown_for_contributors_only(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        assert pre_mod_preprint_v2.machine_state == 'pending'

        withdrawal_request = PreprintRequestFactory(
            creator=self.user,
            target=pre_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.user)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # pending withdrawn original preprint is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # pending withdrawn preprint version is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'
        assert res.status_code == 200

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)

        # pending withdrawn original preprint is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # pending withdrawn preprint version is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        random_user = AuthUserFactory()
        # pending withdrawn original preprint is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

        # pending withdrawn preprint version is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_accepted_preprint_in_pre_moderation_but_not_withdrawn_is_shown_for_everyone(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        pre_mod_preprint_v2.run_accept(self.moderator, 'comment')

        # accepted original preprint is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

        # accepted preprint version is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'
        assert res.status_code == 200

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)

        # accepted original preprint is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

        # accepted preprint version is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

        random_user = AuthUserFactory()
        # accepted original preprint is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

        # accepted preprint version is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

    def test_accepted_preprint_in_pre_moderation_and_withdrawn_is_shown_for_everyone(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        pre_mod_preprint_v2.run_accept(self.moderator, 'comment')

        withdrawal_request = PreprintRequestFactory(
            creator=self.user,
            target=pre_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.user)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # accepted and withdrawn original preprint is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # accepted and withdrawn preprint version is shown for owner
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'
        assert res.status_code == 200

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)

        # accepted and withdrawn original preprint is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # accepted and withdrawn preprint version is shown for contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        random_user = AuthUserFactory()
        # accepted and withdrawn original preprint is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # accepted and withdrawn preprint version is hidden for non-contributors
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=random_user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

    def test_moderator_sees_pending_preprint(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)

        # preprint
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'pending'

        # preprint version
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'pending'

    def test_moderator_sees_pending_withdrawn_preprint(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        assert pre_mod_preprint_v2.machine_state == 'pending'

        withdrawal_request = PreprintRequestFactory(
            creator=self.user,
            target=pre_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.user)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # preprint
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # preprint version
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

    def test_moderator_sees_accepted_preprint(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        pre_mod_preprint_v2.run_accept(self.moderator, 'comment')

        # preprint
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

        # preprint version
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'accepted'

    def test_moderator_sees_withdrawn_preprint(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.user)
        pre_mod_preprint_v2.run_accept(self.moderator, 'comment')

        withdrawal_request = PreprintRequestFactory(
            creator=self.user,
            target=pre_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.user)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # preprint
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

        # preprint version
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['reviews_state'] == 'withdrawn'

    def test_moderator_does_not_see_initial_preprint(self):
        preprint_id = self.pre_mod_preprint._id.split('_')[0]

        contributor = AuthUserFactory()
        self.pre_mod_preprint.add_contributor(contributor, permissions.READ)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=self.pre_mod_preprint,
            final_machine_state='initial',
            creator=self.user,
            set_doi=False
        )

        # preprint
        res = self.app.get(f'/{API_BASE}preprints/{preprint_id}/', auth=self.moderator.auth, expect_errors=True)
        assert res.status_code == 404

        # preprint version
        res = self.app.get(f'/{API_BASE}preprints/{pre_mod_preprint_v2._id}/', auth=self.moderator.auth, expect_errors=True)
        assert res.status_code == 404


class TestPreprintVersionsListRetrieve(ApiTestCase):

    def setUp(self):

        super().setUp()

        self.creator = AuthUserFactory()
        self.read_contrib = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.admin_contrib = AuthUserFactory()
        self.moderator = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

    def test_list_versions_post_mod(self):
        # Post moderation V1 (Accepted)
        post_mod_preprint = PreprintFactory(
            reviews_workflow='post-moderation',
            creator=self.creator,
            is_published=True
        )
        post_mod_preprint.add_contributor(self.admin_contrib, permissions=permissions.ADMIN)
        post_mod_preprint.add_contributor(self.write_contrib, permissions=permissions.WRITE)
        post_mod_preprint.add_contributor(self.read_contrib, permissions=permissions.READ)
        post_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        post_mod_versions_list_url = f"/{API_BASE}preprints/{post_mod_preprint.get_guid()._id}/versions/"

        # Post moderation V2 (Withdrawn)
        post_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=post_mod_preprint,
            creator=self.creator,
            final_machine_state='initial',
            set_doi=False
        )
        post_mod_preprint_v2.run_submit(self.creator)
        post_mod_preprint_v2.run_accept(self.moderator, 'comment')
        withdrawal_request = PreprintRequestFactory(
            creator=self.creator,
            target=post_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.creator)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # Post moderation V3 (Pending)
        post_mod_preprint_v3 = PreprintFactory.create_version(
            create_from=post_mod_preprint_v2,
            creator=self.creator,
            final_machine_state='initial',
            set_doi=False
        )
        post_mod_preprint_v3.run_submit(self.creator)
        id_set = {post_mod_preprint._id, post_mod_preprint_v2._id, post_mod_preprint_v3._id}
        res = self.app.get(post_mod_versions_list_url, auth=self.admin_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([item['id'] for item in data]) == id_set
        res = self.app.get(post_mod_versions_list_url, auth=self.write_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([item['id'] for item in data]) == id_set
        res = self.app.get(post_mod_versions_list_url, auth=self.read_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([item['id'] for item in data]) == id_set
        res = self.app.get(post_mod_versions_list_url, auth=self.non_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([item['id'] for item in data]) == id_set
        res = self.app.get(post_mod_versions_list_url, auth=None)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 3
        assert set([item['id'] for item in data]) == id_set

    def test_list_versions_pre_mod(self):
        # Pre moderation V1 (Accepted)
        pre_mod_preprint = PreprintFactory(
            reviews_workflow='pre-moderation',
            creator=self.creator,
            is_published=True
        )
        pre_mod_preprint.provider.get_group('moderator').user_set.add(self.moderator)
        pre_mod_preprint.add_contributor(self.admin_contrib, permissions=permissions.ADMIN)
        pre_mod_preprint.add_contributor(self.write_contrib, permissions=permissions.WRITE)
        pre_mod_preprint.add_contributor(self.read_contrib, permissions=permissions.READ)
        pre_mod_versions_list_url = f"/{API_BASE}preprints/{pre_mod_preprint.get_guid()._id}/versions/"

        for contrib in pre_mod_preprint.contributor_set.all():
            print(f'>>>> {contrib}:{contrib.permission}')

        # Pre moderation V2 (Withdrawn)
        pre_mod_preprint_v2 = PreprintFactory.create_version(
            create_from=pre_mod_preprint,
            creator=self.creator,
            final_machine_state='initial',
            set_doi=False
        )
        pre_mod_preprint_v2.run_submit(self.creator)
        pre_mod_preprint_v2.run_accept(self.moderator, 'comment')
        withdrawal_request = PreprintRequestFactory(
            creator=self.creator,
            target=pre_mod_preprint_v2,
            request_type=RequestTypes.WITHDRAWAL.value,
            machine_state=DefaultStates.INITIAL.value)
        withdrawal_request.run_submit(self.creator)
        withdrawal_request.run_accept(self.moderator, withdrawal_request.comment)

        # Pre moderation V3 (Rejected)
        pre_mod_preprint_v3 = PreprintFactory.create_version(
            create_from=pre_mod_preprint_v2,
            creator=self.creator,
            final_machine_state='initial',
            is_published=False,
            set_doi=False,
        )
        pre_mod_preprint_v3.run_submit(self.creator)
        pre_mod_preprint_v3.run_reject(self.moderator, 'comment')

        # Pre moderation V4 (Pending)
        pre_mod_preprint_v4 = PreprintFactory.create_version(
            create_from=pre_mod_preprint_v2,
            creator=self.creator,
            final_machine_state='initial',
            is_published=False,
            set_doi=False
        )
        pre_mod_preprint_v4.run_submit(self.creator)

        admin_id_set = {pre_mod_preprint._id, pre_mod_preprint_v2._id, pre_mod_preprint_v3._id, pre_mod_preprint_v4._id}
        non_admin_id_set = {pre_mod_preprint._id, pre_mod_preprint_v2._id}
        res = self.app.get(pre_mod_versions_list_url, auth=self.admin_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 4
        assert set([item['id'] for item in data]) == admin_id_set
        res = self.app.get(pre_mod_versions_list_url, auth=self.write_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert set([item['id'] for item in data]) == non_admin_id_set
        res = self.app.get(pre_mod_versions_list_url, auth=self.read_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert set([item['id'] for item in data]) == non_admin_id_set
        res = self.app.get(pre_mod_versions_list_url, auth=self.non_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert set([item['id'] for item in data]) == non_admin_id_set
        res = self.app.get(pre_mod_versions_list_url, auth=None)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2
        assert set([item['id'] for item in data]) == non_admin_id_set

    def test_invalid_preprint_id(self):
        versions_url_invalid_guid = f'/{API_BASE}preprints/abcde/versions/'
        res = self.app.get(versions_url_invalid_guid, auth=None, expect_errors=True)
        assert res.status_code == 404
        preprint = PreprintFactory(
            reviews_workflow='post-moderation',
            creator=self.creator,
            is_published=True
        )
        versions_url_invalid_version = f'/{API_BASE}preprints/{preprint.get_guid()._id}_v2/versions/'
        res = self.app.get(versions_url_invalid_version, auth=None, expect_errors=True)
        assert res.status_code == 404

    def test_version_indifference(self):
        latest_version = PreprintFactory(
            reviews_workflow='post-moderation',
            creator=self.creator,
            is_published=True
        )
        for _ in range(5):
            new_version = PreprintFactory.create_version(
                create_from=latest_version,
                creator=self.creator,
                set_doi=False
            )
            latest_version = new_version
        versions_url_base_guid = f'/{API_BASE}preprints/{latest_version.get_guid()._id}/versions/'
        res_1 = self.app.get(versions_url_base_guid, auth=self.creator.auth)
        assert res_1.status_code == 200
        versions_url_valid_version = f'/{API_BASE}preprints/{latest_version._id}/versions/'
        res_2 = self.app.get(versions_url_valid_version, auth=self.creator.auth)
        assert res_2.status_code == 200
        assert len(res_1.json['data']) == len(res_2.json['data'])
