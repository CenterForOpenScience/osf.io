# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import AuthUserFactory
from api.base import utils
from api.base.settings.defaults import API_BASE
from osf.models import QuickFilesNode
from addons.osfstorage.models import OsfStorageFile

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestUserQuickFiles:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def quickfiles(self, user):
        return QuickFilesNode.objects.get(creator=user)

    @pytest.fixture(autouse=True)
    def add_quickfiles(self, quickfiles):
        osfstorage = quickfiles.get_addon('osfstorage')
        root = osfstorage.get_root()

        root.append_file('Follow.txt')
        root.append_file('The.txt')
        root.append_file('Buzzards.txt')

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/quickfiles/'.format(API_BASE, user._id)

    def test_authorized_gets_200(self, app, user, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_anonymous_gets_200(self, app, url):
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_get_files_logged_in(self, app, user, url):
        res = app.get(url, auth=user.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert len(ids) == OsfStorageFile.objects.count()

    def test_get_files_not_logged_in(self, app, url):
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert len(ids) == OsfStorageFile.objects.count()

    def test_get_files_logged_in_as_different_user(self, app, user, url):
        user_two = AuthUserFactory()
        res = app.get(url, auth=user_two.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert len(ids) == OsfStorageFile.objects.count()

    def test_get_files_me(self, app, user, quickfiles):
        user_two = AuthUserFactory()
        quickfiles_two = QuickFilesNode.objects.get(creator=user_two)
        osf_storage_two = quickfiles_two.get_addon('osfstorage')
        root_two = osf_storage_two.get_root()

        # these files should not be included in the users/me/files results
        root_two.append_file('Sister.txt')
        root_two.append_file('Abigail.txt')

        url = '/{}users/me/quickfiles/'.format(API_BASE)
        res = app.get(url, auth=user.auth)
        node_json = res.json['data']

        ids_returned = [each['id'] for each in node_json]
        ids_from_files = quickfiles.files.all().values_list('_id', flat=True)
        user_two_file_ids = quickfiles_two.files.all().values_list('_id', flat=True)

        assert sorted(ids_returned) == sorted(ids_from_files)
        for ident in user_two_file_ids:
            assert ident not in ids_returned

    def test_get_files_detail_has_user_relationship(self, app, user, quickfiles):
        file_id = quickfiles.files.all().values_list('_id', flat=True).first()
        url = '/{}files/{}/'.format(API_BASE, file_id)
        res = app.get(url, auth=user.auth)
        file_detail_json = res.json['data']

        assert 'user' in file_detail_json['relationships']
        assert 'node' not in file_detail_json['relationships']
        assert file_detail_json['relationships']['user']['links']['related']['href'].split(
            '/')[-2] == user._id

    def test_get_files_has_links(self, app, user, url, quickfiles):
        res = app.get(url, auth=user.auth)
        file_detail_json = res.json['data'][0]
        waterbutler_url = utils.waterbutler_api_url_for(
            None,
            quickfiles._id,
            'osfstorage',
            file_detail_json['attributes']['path']
        )

        assert 'delete' in file_detail_json['links']
        assert file_detail_json['links']['delete'] == waterbutler_url

        assert 'download' in file_detail_json['links']
        assert file_detail_json['links']['download'] == waterbutler_url

        assert 'info' in file_detail_json['links']

        assert 'move' in file_detail_json['links']
        assert file_detail_json['links']['move'] == waterbutler_url

        assert 'self' in file_detail_json['links']

        assert 'upload' in file_detail_json['links']
        assert file_detail_json['links']['upload'] == waterbutler_url

    def test_disabled_users_quickfiles_gets_410(self, app, user, quickfiles, url):
        user.is_disabled = True
        user.save()
        res = app.get(url, expect_errors=True)
        assert res.status_code == 410
        assert res.content_type == 'application/vnd.api+json'
