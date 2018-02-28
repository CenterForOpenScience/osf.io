import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory,
    NodeFactory
)
from osf.utils import permissions


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
class TestViewOnlyLinksDetail:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(
            API_BASE, public_project._id, view_only_link._id)

    def test_non_mutating_view_only_links_detail_tests(
            self, app, user, write_contrib, read_contrib, non_contrib, url):

        #   test_admin_can_view_vol_detail
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'

    #   test_read_write_cannot_view_vol_detail
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vol_detail
        res = app.get(url, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vol_detail
        res = app.get(url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vol_detail
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_deleted_vol_not_returned(
            self, app, user, public_project, view_only_link, url):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'

        view_only_link.nodes.remove(public_project)
        view_only_link.save()

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestViewOnlyLinksUpdate:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(
            API_BASE, public_project._id, view_only_link._id)

    @pytest.fixture()
    def public_project_admin(self, public_project):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, public_project_admin, public_project):
        public_project.add_contributor(
            public_project_admin, permissions=[
                permissions.ADMIN])
        return public_project

    @pytest.fixture()
    def public_project_component(self, user, public_project):
        return NodeFactory(is_public=True, creator=user, parent=public_project)

    def test_admin_can_update_vol_name(self, app, user, view_only_link, url):
        assert view_only_link.name == 'testlink'
        assert not view_only_link.anonymous

        payload = {
            'attributes': {
                'name': 'updated vol name'
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'updated vol name'
        assert not res.json['data']['attributes']['anonymous']

    def test_admin_can_update_vol_anonymous(
            self, app, user, view_only_link, url):
        assert view_only_link.name == 'testlink'
        assert not view_only_link.anonymous

        payload = {
            'attributes': {
                'anonymous': True
            }
        }
        res = app.put_json_api(url, {'data': payload}, auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'
        assert res.json['data']['attributes']['anonymous']

    def test_cannot_update_vol(
            self, app, write_contrib, read_contrib, non_contrib, url):

        #   test_read_write_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(
            url,
            {'data': payload},
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(
            url,
            {'data': payload},
            auth=read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(
            url,
            {'data': payload},
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_update_vol
        payload = {
            'attributes': {
                'name': 'updated vol name',
                'anonymous': True,
            }
        }
        res = app.put_json_api(url, {'data': payload}, expect_errors=True)
        assert res.status_code == 401


@pytest.mark.django_db
class TestViewOnlyLinksDelete:

    @pytest.fixture()
    def url(self, public_project, view_only_link):
        return '/{}nodes/{}/view_only_links/{}/'.format(
            API_BASE, public_project._id, view_only_link._id)

    def test_admin_can_delete_vol(self, app, user, url, view_only_link):
        res = app.delete(url, auth=user.auth)
        view_only_link.reload()
        assert res.status_code == 204
        assert view_only_link.is_deleted

    def test_vol_delete(
            self, app, write_contrib, read_contrib, non_contrib, url):

        #   test_read_write_cannot_delete_vol
        res = app.delete(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_delete_vol
        res = app.delete(url, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_delete_vol
        res = app.delete(url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_delete_vol
        res = app.delete(url, expect_errors=True)
        assert res.status_code == 401
