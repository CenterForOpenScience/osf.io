import pytest

from osf.utils import permissions
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory
)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def read_contrib():
    return AuthUserFactory()


@pytest.fixture()
def write_contrib():
    return AuthUserFactory()


@pytest.fixture()
def non_contrib():
    return AuthUserFactory()


@pytest.fixture()
def public_project(user, read_contrib, write_contrib):
    public_project = ProjectFactory(is_public=True, creator=user)
    public_project.add_contributor(
        read_contrib, permissions=[permissions.READ])
    public_project.add_contributor(
        write_contrib, permissions=[permissions.READ, permissions.WRITE])
    public_project.save()
    return public_project


@pytest.fixture()
def view_only_link(public_project):
    view_only_link = PrivateLinkFactory(name='testlink')
    view_only_link.nodes.add(public_project)
    view_only_link.save()
    return view_only_link


@pytest.mark.django_db
class TestViewOnlyLinksList:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/'.format(
            API_BASE, public_project._id)

    def test_non_mutating_view_only_links_list_tests(
            self, app, user, write_contrib, read_contrib, non_contrib, url):

        #   test_admin_can_view_vols_list
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['name'] == 'testlink'

    #   test_read_write_cannot_view_vols_list
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vols_list
        res = app.get(url, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vols_list
        res = app.get(url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vols_list
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_deleted_vols_not_returned(self, app, user, url, public_project):
        view_only_link = PrivateLinkFactory(name='testlink2')
        view_only_link.nodes.add(public_project)
        view_only_link.save()

        res = app.get(url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert len(data) == 2

        view_only_link.nodes.remove(public_project)
        view_only_link.save()

        res = app.get(url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert len(data) == 1


@pytest.mark.django_db
class TestViewOnlyLinksCreate:

    @pytest.fixture()
    def url(self, public_project):
        return '/{}nodes/{}/view_only_links/'.format(
            API_BASE, public_project._id)

    def test_invalid_vol_name(self, app, user, url):
        payload = {
            'attributes': {
                'name': '<div>  </div>',
                'anonymous': False,
            }
        }
        res = app.post_json_api(
            url,
            {'data': payload},
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid link name.'

    def test_default_anonymous_not_in_payload(self, app, user, public_project):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(
            API_BASE, public_project._id)
        payload = {
            'attributes': {
                'name': 'testlink',
            }
        }
        res = app.post_json_api(url, {'data': payload}, auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['name'] == 'testlink'
        assert not data['attributes']['anonymous']
        assert data['embeds']['creator']['data']['id'] == user._id

    def test_default_name_not_in_payload(self, app, user, public_project):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(
            API_BASE, public_project._id)
        payload = {
            'attributes': {
                'anonymous': False,
            }
        }
        res = app.post_json_api(url, {'data': payload}, auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert data['attributes']['name'] == 'Shared project link'
        assert not data['attributes']['anonymous']
        assert data['embeds']['creator']['data']['id'] == user._id

    def test_admin_can_create_vol(
            self, app, user, public_project, view_only_link):
        url = '/{}nodes/{}/view_only_links/?embed=creator'.format(
            API_BASE, public_project._id)
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = app.post_json_api(url, {'data': payload}, auth=user.auth)
        assert res.status_code == 201
        assert public_project.private_links.count() == 2
        data = res.json['data']
        assert data['attributes']['name'] == 'testlink'
        assert data['attributes']['anonymous']
        assert data['embeds']['creator']['data']['id'] == user._id

    def test_cannot_create_vol(
            self, app, write_contrib, read_contrib, non_contrib, url):

        #   test_read_write_cannot_create_vol
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = app.post_json_api(
            url,
            {'data': payload},
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_create_vol
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = app.post_json_api(
            url,
            {'data': payload},
            auth=read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_create_vol
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = app.post_json_api(
            url,
            {'data': payload},
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_create_vol
        payload = {
            'attributes': {
                'name': 'testlink',
                'anonymous': True,
            }
        }
        res = app.post_json_api(url, {'data': payload}, expect_errors=True)
        assert res.status_code == 401
