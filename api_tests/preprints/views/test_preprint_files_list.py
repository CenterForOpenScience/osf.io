from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory
)
from osf.utils.permissions import WRITE
from osf.utils.workflows import DefaultStates
from addons.osfstorage.models import OsfStorageFile
from website import settings

class TestPreprintProvidersList(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.url = f'/{API_BASE}preprints/{self.preprint._id}/files/'
        self.user_two = AuthUserFactory()

    def test_published_preprint_files(self):
        # Unauthenticated
        res = self.app.get(self.url)
        assert res.status_code == 200

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_unpublished_preprint_files(self):
        self.preprint.is_published = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_private_preprint_files(self):
        self.preprint.is_public = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_abandoned_preprint_files(self):
        self.preprint.machine_state = DefaultStates.INITIAL.value
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_deleted_preprint_files(self):
        self.preprint.deleted = timezone.now()
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 404

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_withdrawn_preprint_files(self):
        self.preprint.date_withdrawn = timezone.now()
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.url,
        auth=self.user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_return_published_files_logged_out(self):
        res = self.app.get(self.url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['provider'] == 'osfstorage'

    def test_does_not_return_storage_addons_link(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert 'storage_addons' not in res.json['data'][0]['links']

    def test_does_not_return_new_folder_link(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert 'new_folder' not in res.json['data'][0]['links']

    def test_returns_provider_data(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        assert isinstance(res.json['data'], list)
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data'][0]
        assert data['attributes']['kind'] == 'folder'
        assert data['attributes']['name'] == 'osfstorage'
        assert data['attributes']['provider'] == 'osfstorage'
        assert data['attributes']['preprint'] == self.preprint._id
        assert data['attributes']['path'] == '/'
        assert data['attributes']['node'] is None
        assert (
            data['relationships']['target']['links']['related']['href'] ==
            f'{settings.API_DOMAIN}v2/preprints/{self.preprint._id}/'
        )

    def test_osfstorage_file_data_not_found(self):
        res = self.app.get(
            f'{self.url}osfstorage/{self.preprint.primary_file._id}', auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_returns_osfstorage_folder_version_two(self):
        res = self.app.get(
            f'{self.url}osfstorage/', auth=self.user.auth)
        assert res.status_code == 200

    def test_returns_osf_storage_folder_version_two_point_two(self):
        res = self.app.get(
            f'{self.url}osfstorage/?version=2.2', auth=self.user.auth)
        assert res.status_code == 200

    def test_osfstorage_folder_data_not_found(self):
        fobj = self.preprint.root_folder.append_folder('NewFolder')
        fobj.save()

        res = self.app.get(
            f'{self.url}osfstorage/{fobj._id}', auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404


class TestPreprintFilesList(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.url = f'/{API_BASE}preprints/{self.preprint._id}/files/osfstorage/'
        self.user_two = AuthUserFactory()

    def test_published_preprint_files(self):
        # Unauthenticated
        res = self.app.get(self.url)
        assert res.status_code == 200

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_unpublished_preprint_files(self):
        self.preprint.is_published = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_private_preprint_files(self):
        self.preprint.is_public = False
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_abandoned_preprint_files(self):
        self.preprint.machine_state = DefaultStates.INITIAL.value
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

    def test_deleted_preprint_files(self):
        self.preprint.deleted = timezone.now()
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 410

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 410

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 410

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 410

    def test_withdrawn_preprint_files(self):
        self.preprint.date_withdrawn = timezone.now()
        self.preprint.save()

        # Unauthenticated
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contributor
        self.preprint.add_contributor(self.user_two, WRITE, save=True)
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = self.app.get(self.url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_not_just_primary_file_returned(self):
        filename = 'my second file'
        second_file = OsfStorageFile.create(
            target_object_id=self.preprint.id,
            target_content_type=ContentType.objects.get_for_model(self.preprint),
            path=f'/{filename}',
            name=filename,
            materialized_path=f'/{filename}')

        second_file.save()
        from addons.osfstorage import settings as osfstorage_settings

        second_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()
        second_file.parent = self.preprint.root_folder
        second_file.save()

        assert len(self.preprint.files.all()) == 2
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200

        data = res.json['data']
        assert len(data) == 2
        assert {item['id'] for item in data} == {second_file._id, self.preprint.primary_file._id}

    def test_nested_file_as_primary_file_is_returned(self):
        # Primary file can be any file nested somewhere under the preprint's root folder.
        subfolder = self.preprint.root_folder.append_folder('subfolder')
        subfolder.save()

        primary_file = self.preprint.primary_file

        primary_file.move_under(subfolder)
        primary_file.save()

        assert subfolder.children[0] == primary_file
        assert primary_file.parent == subfolder

        res = self.app.get(self.url, auth=self.user.auth)
        assert len(res.json['data']) == 1

        data = res.json['data'][0]
        assert data['id'] == subfolder._id
        assert data['attributes']['kind'] == 'folder'
        assert data['attributes']['path'] == f'/{subfolder._id}/'
        assert data['attributes']['materialized_path'] == f'/{subfolder.name}/'

    def test_cannot_access_other_addons(self):
        url = f'/{API_BASE}preprints/{self.preprint._id}/files/github/'
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 404
