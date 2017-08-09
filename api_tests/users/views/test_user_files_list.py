# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import AuthUserFactory
from api.base.settings.defaults import API_BASE
from osf.models import QuickFiles, BaseFileNode


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def quickfiles(user):
    return QuickFiles.objects.get(creator=user)


@pytest.mark.django_db
class TestUserQuickFiles:

    @pytest.fixture(autouse=True)
    def add_quickfiles(self, quickfiles):
        osfstorage = quickfiles.get_addon('osfstorage')
        root = osfstorage.get_root()

        root.append_file('Follow.txt')
        root.append_file('The.txt')
        root.append_file('Buzzards.txt')

    def test_authorized_gets_200(self, app, user):
        url = "/{}users/{}/files/".format(API_BASE, user._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_anonymous_gets_200(self, app, user):
        url = "/{}users/{}/files/".format(API_BASE, user._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_get_files_logged_in(self, app, user):
        url = "/{}users/{}/files/".format(API_BASE, user._id)
        res = app.get(url, auth=user.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]

        assert len(ids) == BaseFileNode.objects.filter(type='osf.osfstoragefile').count()

    def test_get_files_not_logged_in(self, app, user):
        url = "/{}users/{}/files/".format(API_BASE, user._id)
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert len(ids) == BaseFileNode.objects.filter(type='osf.osfstoragefile').count()

    def test_get_files_logged_in_as_different_user(self, app, user):
        user_two = AuthUserFactory()
        url = "/{}users/{}/files/".format(API_BASE, user._id)
        res = app.get(url, auth=user_two.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert len(ids) == BaseFileNode.objects.filter(type='osf.osfstoragefile').count()

    def test_get_files_me(self, app, user):
        user_two = AuthUserFactory()
        quickfiles_two = QuickFiles.objects.get(creator=user_two)
        osf_storage_two = quickfiles_two.get_addon('osfstorage')
        root_two = osf_storage_two.get_root()

        # these files should not be included in the users/me/files results
        root_two.append_file('Sister.txt')
        root_two.append_file('Abigail.txt')

        url = "/{}users/me/files/".format(API_BASE)
        res = app.get(url, auth=user.auth)
        node_json = res.json['data']

        ids_returned = [each['id'] for each in node_json]
        ids_from_files = BaseFileNode.objects.filter(type='osf.osfstoragefile', node__creator=user).values_list('_id', flat=True)
        user_two_file_ids = BaseFileNode.objects.filter(type='osf.osfstoragefile', node__creator=user_two).values_list('_id', flat=True)

        assert sorted(ids_returned) == sorted(ids_from_files)
        for ident in user_two_file_ids:
            assert ident not in ids_returned
