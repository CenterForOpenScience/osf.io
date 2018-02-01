import pytest

from website.util import permissions
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory
)


@pytest.mark.django_db
class TestViewOnlyLinksDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_only_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_write_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, user, read_only_user, read_write_user):
        public_project = ProjectFactory(is_public=True, creator=user)
        public_project.add_contributor(
            read_only_user, permissions=[permissions.READ])
        public_project.add_contributor(
            read_write_user, permissions=[permissions.WRITE])
        public_project.save()
        return public_project

    @pytest.fixture()
    def view_only_link(self, public_project):
        view_only_link = PrivateLinkFactory(name='testlink')
        view_only_link.nodes.add(public_project)
        view_only_link.save()
        return view_only_link

    @pytest.fixture()
    def url(self, view_only_link):
        return '/{}view_only_links/{}/'.format(API_BASE, view_only_link._id)

    def test_view_only_links_detail(
            self, app, user, read_only_user, read_write_user,
            non_contributor, url):

        #   test_admin_can_view_vol_detail
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'testlink'

    #   test_read_write_cannot_view_vol_detail
        res = app.get(url, auth=read_write_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_cannot_view_vol_detail
        res = app.get(url, auth=read_only_user.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_user_cannot_view_vol_detail
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_vol_detail
        res = app.get(url, expect_errors=True)
        assert res.status_code == 403
