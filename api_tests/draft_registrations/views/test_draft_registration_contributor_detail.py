import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_contributors_detail import (
    TestContributorDetail,
    TestNodeContributorOrdering,
    TestNodeContributorUpdate,
    TestNodeContributorPartialUpdate,
    TestNodeContributorDelete
)
from osf_tests.factories import (
    DraftRegistrationFactory,
    ProjectFactory,
    AuthUserFactory
)
from osf.utils import permissions


@pytest.fixture()
def user():
    return AuthUserFactory(given_name='Dawn')


class TestDraftContributorDetail(TestContributorDetail):
    @pytest.fixture()
    def project_public(self, user, title, description, category):
        # Defining "project public" as a draft reg, overriding TestContributorDetail
        project = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )
        draft = DraftRegistrationFactory(
            initiator=user,
            branched_from=project,
        )
        return draft

    @pytest.fixture()
    def project_private(self, user, title, description, category):
        # Defining "private project" as a draft reg, overriding TestContributorDetail
        draft = DraftRegistrationFactory(
            initiator=user,
        )
        return draft

    @pytest.fixture()
    def url_public(self, user, project_public):
        # Overrides TestContributorDetail
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project_public._id, user._id)

    @pytest.fixture()
    def url_private_base(self, project_private):
        # Overrides TestContributorDetail
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project_private._id, '{}')

    @pytest.fixture()
    def url_private(self, user, url_private_base):
        return url_private_base.format(user._id)

    @pytest.fixture()
    def make_resource_url(self):
        # Overrides TestContributorDetail
        def make_resource_url(resource_id, user_id):
            return '/{}draft_registrations/{}/contributors/{}/'.format(
                API_BASE, resource_id, user_id)
        return make_resource_url

    # Overrides TestContributorDetail
    def test_get_contributor_detail_valid_response(
            self, app, user, project_public,
            project_private, url_public, url_private):

        #   test_get_public_contributor_detail
        res = app.get(url_public, expect_errors=True)
        assert res.status_code == 401

    #   regression test
    #   test_get_public_contributor_detail_is_viewable_through_browsable_api
        res = app.get(url_public + '?format=api', auth=user.auth)
        assert res.status_code == 200

    #   test_get_private_node_contributor_detail_contributor_auth
        res = app.get(url_private, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == '{}-{}'.format(
            project_private._id, user._id)

    # Overrides TestContributorDetail
    def test_node_contributor_detail_serializes_contributor_perms(self, app, user, make_resource_url, project_public):
        user_two = AuthUserFactory()
        project_public.add_contributor(user_two, permissions.WRITE)
        project_public.save()

        url = make_resource_url(project_public._id, user_two._id)
        res = app.get(url, auth=user.auth)
        # Even though user_two has admin perms through group membership,
        # contributor endpoints return contributor permissions
        assert res.json['data']['attributes']['permission'] == permissions.WRITE
        assert project_public.has_permission(user_two, permissions.WRITE) is True


class TestDraftContributorOrdering(TestNodeContributorOrdering):
    @pytest.fixture()
    def project(self, user, contribs):
        # Overrides TestNodeContributorOrdering
        project = DraftRegistrationFactory(initiator=user, title='hey')
        for contrib in contribs:
            if contrib._id != user._id:
                project.add_contributor(
                    contrib,
                    permissions=permissions.WRITE,
                    visible=True,
                    save=True
                )
        return project

    @pytest.fixture()
    def url_contrib_base(self, project):
        # Overrides TestNodeContributorOrdering
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project._id)

    @pytest.fixture()
    def url_creator(self, user, project):
        # Overrides TestNodeContributorOrdering
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user._id)

    @pytest.fixture()
    def urls_contrib(self, contribs, project):
        # Overrides TestNodeContributorOrdering
        return [
            '/{}draft_registrations/{}/contributors/{}/'.format(
                API_BASE,
                project._id,
                contrib._id) for contrib in contribs]


class TestDraftRegistrationContributorUpdate(TestNodeContributorUpdate):

    @pytest.fixture()
    def project(self, user, contrib):
        # Overrides TestNodeContributorUpdate
        draft = DraftRegistrationFactory(creator=user)
        draft.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)
        return draft

    @pytest.fixture()
    def url_creator(self, user, project):
        # Overrides TestNodeContributorUpdate
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user._id)

    @pytest.fixture()
    def url_contrib(self, project, contrib):
        # Overrides TestNodeContributorUpdate
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, contrib._id)

    def test_change_contributor_non_admin_osf_group_member_auth(self, project, contrib):
        # Overrides TestNodeContributorUpdate - drafts have no group perms
        return

    def test_change_contributor_admin_osf_group_permissions(self, project, contrib):
        # Overrides TestNodeContributorUpdate - drafts have no group perms
        return


class TestDraftRegistrationContributorPartialUpdate(TestNodeContributorPartialUpdate):
    @pytest.fixture()
    def contrib(self):
        # Overrides TestNodeContributorPartialUpdate
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user, contrib):
        # Overrides TestNodeContributorPartialUpdate
        project = DraftRegistrationFactory(creator=user)
        project.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)
        return project

    @pytest.fixture()
    def url_creator(self, user, project):
        # Overrides TestNodeContributorPartialUpdate
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user._id)

    @pytest.fixture()
    def url_contrib(self, contrib, project):
        # Overrides TestNodeContributorPartialUpdate
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, self.project._id, self.user_two._id)

    def test_patch_permission_only(self, app, user, project):
        # Overrides TestNodeContributorPartialUpdate
        user_read_contrib = AuthUserFactory()
        project.add_contributor(
            user_read_contrib,
            permissions=permissions.WRITE,
            visible=False,
            save=True)
        url_read_contrib = '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user_read_contrib._id)
        contributor_id = '{}-{}'.format(project._id, user_read_contrib._id)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                }
            }
        }
        res = app.patch_json_api(url_read_contrib, data, auth=user.auth)
        assert res.status_code == 200
        project.reload()
        assert project.get_permissions(user_read_contrib) == [permissions.READ]
        assert not project.get_visible(user_read_contrib)


class TestDraftContributorDelete(TestNodeContributorDelete):
    @pytest.fixture()
    def project(self, user, user_write_contrib):
        # Overrides TestNodeContributorDelete
        project = DraftRegistrationFactory(creator=user)
        project.add_contributor(
            user_write_contrib,
            permissions=permissions.WRITE,
            visible=True, save=True)
        return project

    @pytest.fixture()
    def url_user(self, project, user):
        # Overrides TestNodeContributorDelete
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user._id)

    @pytest.fixture()
    def url_user_write_contrib(self, project, user_write_contrib):
        # Overrides TestNodeContributorDelete
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user_write_contrib._id)

    @pytest.fixture()
    def url_user_non_contrib(self, project, user_non_contrib):
        # Overrides TestNodeContributorDelete
        return '/{}draft_registrations/{}/contributors/{}/'.format(
            API_BASE, project._id, user_non_contrib._id)

    def test_remove_contributor_osf_group_member_read(self):
        # Overrides TestNodeContributorDelete - drafts don't have group members
        return

    def test_remove_contributor_osf_group_member_admin(self):
        # Overrides TestNodeContributorDelete - drafts don't have group members
        return
