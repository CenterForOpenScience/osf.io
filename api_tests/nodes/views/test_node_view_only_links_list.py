import pytest

from website.util import permissions
from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory
)


class ViewOnlyLinkTestCase(object):

    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.read_only_user = AuthUserFactory()
        self.read_write_user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.read_only_user, permissions=[permissions.READ])
        self.public_project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.public_project.save()

        self.view_only_link = PrivateLinkFactory(name='testlink')
        self.view_only_link.nodes.add(self.public_project)
        self.view_only_link.save()

@pytest.mark.django_db
class TestViewOnlyLinksList(ViewOnlyLinkTestCase):

    @pytest.fixture(autouse=True)
    def setUp(self):
        super(TestViewOnlyLinksList, self).setUp()
        self.url = '/{}nodes/{}/view_only_links/'.format(API_BASE, self.public_project._id)

    def test_non_mutating_view_only_links_list_tests(self):

    #   test_admin_can_view_vols_list
        res = self.app.get(self.url, auth=self.user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['name'] == 'testlink'

    #   test_read_write_cannot_view_vols_list
        res = self.app.get(self.url, auth=self.read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vols_list
        res = self.app.get(self.url, auth=self.read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vols_list
        res = self.app.get(self.url, auth=self.non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vols_list
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

    def test_deleted_vols_not_returned(self):
        view_only_link = PrivateLinkFactory(name='testlink2')
        view_only_link.nodes.add(self.public_project)
        view_only_link.save()

        res = self.app.get(self.url, auth=self.user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert len(data) == 2

        view_only_link.nodes.remove(self.public_project)
        view_only_link.save()

        res = self.app.get(self.url, auth=self.user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert len(data) == 1

@pytest.mark.django_db
class TestViewOnlyLinksCreate(ViewOnlyLinkTestCase):

    @pytest.fixture(autouse=True)
    def setUp(self):
        super(TestViewOnlyLinksCreate, self).setUp()
        self.url = '/{}nodes/{}/view_only_links/'.format(API_BASE, self.public_project._id)

    def test_invalid_vol_name(self):
        payload = {
            'attributes': {
                'name': '<div>  </div>',
                'anonymous': False,
            }
        }
        res = self.app.post_json_api(self.url, {'data': payload}, auth=self.user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid link name.'

    def test_default_anonymous_not_in_payload(self):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(API_BASE, self.public_project._id)
        payload = {
            'attributes': {
                'name': 'testlink',
            }
        }
        res = self.app.post_json_api(url, {'data': payload}, auth=self.user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['name'] == 'testlink'
        assert data['attributes']['anonymous'] == False
        assert data['embeds']['creator']['data']['id'] == self.user._id

    def test_default_name_not_in_payload(self):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(API_BASE, self.public_project._id)
        payload = {
            'attributes': {
                'anonymous': False,
            }
        }
        res = self.app.post_json_api(url, {'data': payload}, auth=self.user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['name'] == 'Shared project link'
        assert data['attributes']['anonymous'] == False
        assert data['embeds']['creator']['data']['id'] == self.user._id

    def test_admin_can_create_vol(self):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(API_BASE, self.public_project._id)
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = self.app.post_json_api(url, {'data': payload}, auth=self.user.auth)
        assert res.status_code == 201
        assert self.public_project.private_links.count() == 2
        data = res.json['data']
        assert data['attributes']['name'] == 'testlink'
        assert data['attributes']['anonymous'] == True
        assert data['embeds']['creator']['data']['id'] == self.user._id

    def test_read_write_cannot_create_vol(self):
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = self.app.post_json_api(self.url, {'data': payload}, auth=self.read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_read_only_cannot_create_vol(self):
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = self.app.post_json_api(self.url, {'data': payload}, auth=self.read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_logged_in_user_cannot_create_vol(self):
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = self.app.post_json_api(self.url, {'data': payload}, auth=self.non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    def test_unauthenticated_user_cannot_create_vol(self):
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = self.app.post_json_api(self.url, {'data': payload}, expect_errors=True)
        assert res.status_code == 401
