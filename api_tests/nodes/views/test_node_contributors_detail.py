import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import NodeLog
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
from tests.utils import assert_latest_log
from osf.utils import permissions
from api_tests.utils import disconnected_from_listeners
from website.project.signals import contributor_removed


class ContributorDetailMixin:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def title(self):
        return 'Cool Project'

    @pytest.fixture()
    def description(self):
        return 'A Properly Cool Project'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def project_public(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )

    @pytest.fixture()
    def project_private(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )

    def make_resource_url(self, resource_id, user_id):
        return f'/{API_BASE}nodes/{resource_id}/contributors/{user_id}/'

    @pytest.fixture()
    def url_public(self, user, project_public):
        return f'/{API_BASE}nodes/{project_public._id}/contributors/{user._id}/'

    def url_private(self, node, user_id):
        return f'/{API_BASE}nodes/{node._id}/contributors/{user_id}/'

@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestContributorDetail(ContributorDetailMixin):
    def test_get_public_contributor_detail(self, app, user, project_public, project_private, url_public):
        res = app.get(url_public)
        assert res.status_code == 200
        assert res.json['data']['id'] == f'{project_public._id}-{user._id}'

    def test_get_public_contributor_detail_is_viewable_through_browsable_api(
            self, app, user, project_public, project_private, url_public):
        res = app.get(f'{url_public}?format=api')
        assert res.status_code == 200

    def test_get_private_node_contributor_detail_contributor_auth(self, app, user, project_public, project_private,
                                                                  url_public):

        res = app.get(
            self.url_private(project_private, user._id),
            auth=user.auth)

        assert res.status_code == 200
        assert res.json['data']['id'] == f'{project_private._id}-{user._id}'

    def test_get_private_node_contributor_detail_non_contributor(self, app, user, project_private):
        non_contrib = AuthUserFactory()
        res = app.get(
            self.url_private(project_private, user._id),
            auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_private_node_contributor_detail_not_logged_in(self, app, user, project_private):
        res = app.get(
            self.url_private(project_private, user._id),
            expect_errors=True
        )
        assert res.status_code == 401

    def test_get_private_node_contributor_detail_not_found(self, app, user, non_contrib, project_private):
        res = app.get(
            self.url_private(project_private, non_contrib._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_get_private_node_invalid_user_detail_contributor_auth(self, app, user, project_private):
        res = app.get(
            self.url_private(project_private, 'invalid'),
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_unregistered_contributor_detail_show_up_as_name_associated_with_project(self, app, user, project_public,
            project_private):
        project_public.add_unregistered_contributor(
            'Rheisen Dennis',
            'reason@gmail.com',
            auth=Auth(user),
        )
        unregistered_contributor = project_public.contributors[1]
        url = self.make_resource_url(project_public._id, unregistered_contributor._id)

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['embeds']['users']['data']['attributes']['full_name'] == 'Rheisen Dennis'
        assert res.json['data']['attributes'].get('unregistered_contributor') == 'Rheisen Dennis'

        project_private.add_unregistered_contributor(
            'Nesiehr Sinned',
            'reason@gmail.com',
            auth=Auth(user),
        )
        url = self.make_resource_url(project_private._id, unregistered_contributor._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        assert res.json['data']['embeds']['users']['data']['attributes']['full_name'] == 'Rheisen Dennis'
        assert res.json['data']['attributes'].get('unregistered_contributor') == 'Nesiehr Sinned'

    def test_detail_includes_index(self, app, user, project_public, url_public):
        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert 'index' in data['attributes'].keys()
        assert data['attributes']['index'] == 0

        other_contributor = AuthUserFactory()
        project_public.add_contributor(
            other_contributor,
            auth=Auth(user),
            save=True
        )
        res = app.get(
            self.make_resource_url(
                project_public._id,
                other_contributor._id
            ),
            auth=user.auth
        )
        assert res.json['data']['attributes']['index'] == 1


class TestNodeContributorDetail(TestContributorDetail):

    def test_detail_includes_is_curator(
            self,
            app,
            user,
            project_public,
            url_public):
        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert 'is_curator' in data['attributes'].keys()
        assert data['attributes']['is_curator'] is False

        other_contributor = AuthUserFactory()
        project_public.add_contributor(
            other_contributor,
            auth=Auth(user),
            save=True,
            notification_type=False
        )

        other_contributor_detail = self.make_resource_url(project_public._id, other_contributor._id)

        res = app.get(other_contributor_detail, auth=user.auth)
        assert res.json['data']['attributes']['is_curator'] is False

        curator_contributor = AuthUserFactory()
        project_public.add_contributor(
            curator_contributor,
            auth=Auth(user),
            save=True,
            make_curator=True,
            visible=False,
            notification_type=False
        )

        curator_contributor_detail = self.make_resource_url(project_public._id, curator_contributor._id)

        res = app.get(curator_contributor_detail, auth=user.auth)
        assert res.json['data']['attributes']['is_curator'] is True


@pytest.mark.django_db
class TestNodeContributorPartialUpdate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user, contrib):
        project = ProjectFactory(creator=user)
        project.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)
        return project

    @pytest.fixture()
    def url_creator(self, user, project):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user._id}/'

    @pytest.fixture()
    def url_contrib(self, contrib, project):
        return f'/{API_BASE}nodes/{self.project._id}/contributors/{self.user_two._id}/'

    def test_patch_bibliographic_only(self, app, user, project, url_creator):
        res = app.patch_json_api(
            url_creator,
            {
                'data': {
                    'id': f'{project._id}-{user._id}',
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': False,
                    }
                }
            },
            auth=user.auth
        )
        assert res.status_code == 200
        assert project.get_permissions(user) == [permissions.READ, permissions.WRITE, permissions.ADMIN]
        assert not project.get_visible(user)

    def test_patch_permission_only(self, app, user, project):
        user_read_contrib = AuthUserFactory()
        project.add_contributor(
            user_read_contrib,
            permissions=permissions.WRITE,
            visible=False,
            save=True
        )
        res = app.patch_json_api(
            f'/{API_BASE}nodes/{project._id}/contributors/{user_read_contrib._id}/',
            {
                'data': {
                    'id': f'{project._id}-{user_read_contrib._id}',
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                    }
                }
            },
            auth=user.auth
        )
        assert res.status_code == 200
        assert project.get_permissions(user_read_contrib) == [permissions.READ]
        assert not project.get_visible(user_read_contrib)


@pytest.mark.django_db
class TestNodeContributorDelete:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user, user_write_contrib):
        project = ProjectFactory(creator=user)
        project.add_contributor(
            user_write_contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True
        )
        return project

    @pytest.fixture()
    def url_user(self, project, user):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user._id}/'

    @pytest.fixture()
    def url_user_write_contrib(self, project, user_write_contrib):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user_write_contrib._id}/'

    @pytest.fixture()
    def url_user_non_contrib(self, project, user_non_contrib):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user_non_contrib._id}/'

    def test_remove_contributor_non_contributor(self, app, user_write_contrib, user_non_contrib, project, url_user,
                                                url_user_write_contrib, url_user_non_contrib):
        res = app.delete(
            url_user_write_contrib,
            auth=user_non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_remove_contributor_not_logged_in(self, app, user_write_contrib, user_non_contrib, project, url_user,
            url_user_write_contrib, url_user_non_contrib):
        res = app.delete(
            url_user_write_contrib,
            expect_errors=True
        )
        assert res.status_code == 401
        assert user_write_contrib in project.contributors

    def test_remove_non_contributor_admin(self, app, user, user_write_contrib, user_non_contrib, project, url_user,
            url_user_write_contrib, url_user_non_contrib):
        assert user_non_contrib not in project.contributors
        res = app.delete(
            url_user_non_contrib,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404
        assert user_non_contrib not in project.contributors

    def test_remove_non_existing_user_admin(self, app, user, user_write_contrib, user_non_contrib, project, url_user,
            url_user_write_contrib, url_user_non_contrib):
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete(
                f'/{API_BASE}nodes/{project._id}/contributors/fake/',
                auth=user.auth,
                expect_errors=True
            )
        assert res.status_code == 404

    def test_remove_self_contributor_unique_admin(self, app, user, user_write_contrib, user_non_contrib, project,
            url_user, url_user_write_contrib, url_user_non_contrib):
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete(url_user, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert user in project.contributors

    def test_can_not_remove_only_bibliographic_contributor(self, app, user, project, user_write_contrib, url_user):
        project.add_permission(
            user_write_contrib,
            permissions.ADMIN,
            save=True
        )
        project.set_visible(
            user_write_contrib,
            False,
            save=True
        )
        res = app.delete(
            url_user,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert user in project.contributors

    def test_remove_contributor_non_admin_is_forbidden(self, app, user_write_contrib, user_non_contrib, project,
            url_user_non_contrib):
        project.add_contributor(
            user_non_contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True
        )

        res = app.delete(
            url_user_non_contrib,
            auth=user_write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert user_non_contrib in project.contributors

    def test_remove_contributor_admin(self, app, user, user_write_contrib, project, url_user_write_contrib):
        with assert_latest_log(NodeLog.CONTRIB_REMOVED, project):
            # Disconnect contributor_removed so that we don't check in files
            # We can remove this when StoredFileNode is implemented in
            # osf-models
            with disconnected_from_listeners(contributor_removed):
                res = app.delete(url_user_write_contrib, auth=user.auth)
            assert res.status_code == 204
            assert user_write_contrib not in project.contributors

    def test_remove_self_non_admin(self, app, user_non_contrib, project, url_user_non_contrib):
        with assert_latest_log(NodeLog.CONTRIB_REMOVED, project):
            project.add_contributor(
                user_non_contrib,
                permissions=permissions.WRITE,
                visible=True,
                save=True)

            # Disconnect contributor_removed so that we don't check in files
            # We can remove this when StoredFileNode is implemented in
            # osf-models
            with disconnected_from_listeners(contributor_removed):
                res = app.delete(
                    url_user_non_contrib,
                    auth=user_non_contrib.auth)
            assert res.status_code == 204
            assert user_non_contrib not in project.contributors

    def test_remove_self_contributor_not_unique_admin(self, app, user, user_write_contrib, project, url_user):
        with assert_latest_log(NodeLog.CONTRIB_REMOVED, project):
            project.add_permission(
                user_write_contrib,
                permissions.ADMIN,
                save=True
            )
            # Disconnect contributor_removed so that we don't check in files
            # We can remove this when StoredFileNode is implemented in
            # osf-models
            with disconnected_from_listeners(contributor_removed):
                res = app.delete(url_user, auth=user.auth)
            assert res.status_code == 204
            assert user not in project.contributors

    def test_can_remove_self_as_contributor_not_unique_admin(self, app, user_write_contrib, project,
            url_user_write_contrib):
        with assert_latest_log(NodeLog.CONTRIB_REMOVED, project):
            project.add_permission(
                user_write_contrib,
                permissions.ADMIN,
                save=True
            )
            # Disconnect contributor_removed so that we don't check in files
            # We can remove this when StoredFileNode is implemented in
            # osf-models
            with disconnected_from_listeners(contributor_removed):
                res = app.delete(
                    url_user_write_contrib,
                    auth=user_write_contrib.auth
                )
            assert res.status_code == 204
            assert user_write_contrib not in project.contributors
