import pytest
from framework import utils

from addons.osfstorage.models import OsfStorageFile
from api.base.settings.defaults import API_BASE
from django.core.urlresolvers import reverse


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestUserQuickFiles:
    """ UserQuickFiles """

    @pytest.fixture(autouse=True)
    def add_quickfiles(self, user):
        user.quickfolder.append_file('Follow.txt')
        user.quickfolder.append_file('The.txt')
        user.quickfolder.append_file('Buzzards.txt')

    @pytest.fixture()
    def url(self, user):
        return reverse('users:user-quickfiles', kwargs={'version': 'v2', 'user_id': user._id})

    def test_authorized_gets_200(self, django_app, user, url):
        res = django_app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_anonymous_gets_200(self, django_app, user, url):
        res = django_app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        files = OsfStorageFile.objects.filter(_id__in=ids)
        assert list(files) == list(user.quickfiles)

    def test_get_files_logged_in_as_different_user(self, django_app, url, user2):
        res = django_app.get(url, auth=user2.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert len(ids) == OsfStorageFile.objects.count()

    def test_get_files_has_links(self, django_app, user, url):
        res = django_app.get(url, auth=user.auth)
        file_detail_json = res.json['data'][0]
        waterbutler_url = utils.waterbutler_api_url_for(
            user._id,
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

    def test_disabled_user_gets_410(self, django_app, user, url):
        user.is_disabled = True
        user.save()

        res = django_app.get(url, expect_errors=True)
        assert res.status_code == 410
        assert res.content_type == 'application/vnd.api+json'

    def test_get_files_me(self, django_app, user, user2):

        # these files should not be included in the users/me/files results
        user2.quickfolder.append_file('Sister.txt')
        user2.quickfolder.append_file('Abigail.txt')

        url = '/{}users/{}/quickfiles/'.format(API_BASE, 'me')
        res = django_app.get(url, auth=user.auth)
        node_json = res.json['data']

        ids_returned = [each['id'] for each in node_json]
        ids_from_files = user.quickfiles.values_list('_id', flat=True)
        user2_file_ids = user2.quickfiles.values_list('_id', flat=True)

        assert sorted(ids_returned) == sorted(ids_from_files)
        for ident in user2_file_ids:
            assert ident not in ids_returned
