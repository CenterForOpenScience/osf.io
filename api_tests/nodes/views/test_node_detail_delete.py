from unittest import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.utils import NodeCRUDTestCase
from osf.models import NodeLog
from osf.utils import permissions
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    AuthUserFactory,
    PreprintFactory,
    IdentifierFactory,
)
from tests.utils import assert_latest_log
from website.views import find_bookmark_collection


@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
class TestNodeDelete(NodeCRUDTestCase):

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    def test_deletes_public_node_logged_out(
        self, app, user, user_two, project_public, project_private, url_public, url_private, url_fake
    ):

        #   test_deletes_public_node_logged_out
        res = app.delete(url_public, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_deletes_public_node_fails_if_unauthorized(
            self, app, user, user_two, project_public, project_private, url_public, url_private, url_fake
    ):
        res = app.delete_json_api(
            url_public,
            auth=user_two.auth,
            expect_errors=True)
        project_public.reload()
        assert res.status_code == 403
        assert project_public.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_out(
        self, app, user, user_two, project_public, project_private, url_public, url_private, url_fake
    ):
        res = app.delete(url_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_non_contributor(
        self, app, user, user_two, project_public, project_private, url_public, url_private, url_fake
    ):
        res = app.delete(url_private, auth=user_two.auth, expect_errors=True)
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_deletes_invalid_node(
        self, app, user, user_two, project_public, project_private, url_public, url_private, url_fake
    ):
        res = app.delete(url_fake, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_read_only_contributor(self, app, user_two, project_private, url_private):
        project_private.add_contributor(
            user_two,
            permissions=permissions.READ
        )
        project_private.save()
        res = app.delete(
            url_private,
            auth=user_two.auth,
            expect_errors=True
        )
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_write_contributor(self, app, user_two, project_private, url_private):
        project_private.add_contributor(
            user_two,
            permissions=permissions.WRITE
        )
        project_private.save()
        res = app.delete(
            url_private,
            auth=user_two.auth,
            expect_errors=True
        )
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_delete_project_with_component_returns_errors_pre_2_12(self, app, user):
        project = ProjectFactory(creator=user)
        NodeFactory(parent=project, creator=user)
        # Return a 400 because component must be deleted before deleting the
        # parent
        res = app.delete_json_api(
            f'/{API_BASE}nodes/{project._id}/',
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert (
            errors[0]['detail'] ==
            'Any child components must be deleted prior to deleting this project.')

    def test_delete_project_with_component_allowed_with_2_12(self, app, user):
        project = ProjectFactory(creator=user)
        child = NodeFactory(parent=project, creator=user)
        grandchild = NodeFactory(parent=child, creator=user)
        # Versions 2.12 and greater delete all the nodes in the hierarchy
        res = app.delete_json_api(
            f'/{API_BASE}nodes/{project._id}/?version=2.12',
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 204
        project.reload()
        child.reload()
        grandchild.reload()
        assert project.is_deleted is True
        assert child.is_deleted is True
        assert grandchild.is_deleted is True

    def test_delete_project_with_private_component_2_12(self, app, user):
        user_two = AuthUserFactory()
        project = ProjectFactory(creator=user)
        child = NodeFactory(parent=project, creator=user_two)
        # Versions 2.12 and greater delete all the nodes in the hierarchy
        res = app.delete_json_api(
            f'/{API_BASE}nodes/{project._id}/?version=2.12',
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        project.reload()
        child.reload()
        assert project.is_deleted is False
        assert child.is_deleted is False

    def test_delete_bookmark_collection_returns_error(self, app, user):
        bookmark_collection = find_bookmark_collection(user)
        res = app.delete_json_api(
            f'/{API_BASE}nodes/{bookmark_collection._id}/',
            auth=user.auth,
            expect_errors=True
        )
        # Bookmark collections are collections, so a 404 is returned
        assert res.status_code == 404

    @mock.patch('website.identifiers.tasks.update_doi_metadata_on_change')
    def test_delete_node_with_preprint_calls_preprint_update_status(
        self, mock_update_doi_metadata_on_change, app, user, project_public, url_public
    ):
        PreprintFactory(project=project_public)
        app.delete_json_api(url_public, auth=user.auth, expect_errors=True)
        project_public.reload()

        assert not mock_update_doi_metadata_on_change.called

    @mock.patch('website.identifiers.tasks.update_doi_metadata_on_change')
    def test_delete_node_with_identifier_calls_preprint_update_status(
            self, mock_update_doi_metadata_on_change, app, user, project_public, url_public
    ):
        IdentifierFactory(referent=project_public, category='doi')
        app.delete_json_api(url_public, auth=user.auth, expect_errors=True)
        project_public.reload()

        assert mock_update_doi_metadata_on_change.called

    def test_deletes_public_node_succeeds_as_owner(self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.PROJECT_DELETED, project_public):
            res = app.delete_json_api(
                url_public, auth=user.auth, expect_errors=True)
            project_public.reload()
            assert res.status_code == 204
            assert project_public.is_deleted is True

    def test_requesting_deleted_returns_410(self, app, project_public, url_public):
        project_public.is_deleted = True
        project_public.save()
        res = app.get(url_public, expect_errors=True)
        assert res.status_code == 410
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_contributor(self, app, user, project_private, url_private):
        with assert_latest_log(NodeLog.PROJECT_DELETED, project_private):
            res = app.delete(url_private, auth=user.auth, expect_errors=True)
            project_private.reload()
            assert res.status_code == 204
            assert project_private.is_deleted is True


@pytest.mark.django_db
class TestReturnDeletedNode:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public_deleted(self, user):
        return ProjectFactory(
            is_deleted=True,
            creator=user,
            title='This public project has been deleted',
            category='project',
            is_public=True
        )

    @pytest.fixture()
    def project_private_deleted(self, user):
        return ProjectFactory(
            is_deleted=True,
            creator=user,
            title='This private project has been deleted',
            category='project',
            is_public=False
        )

    @pytest.fixture()
    def title_new(self):
        return 'This deleted node has been edited'

    @pytest.fixture()
    def url_project_public_deleted(self, project_public_deleted):
        return f'/{API_BASE}nodes/{project_public_deleted._id}/'

    @pytest.fixture()
    def url_project_private_deleted(self, project_private_deleted):
        return f'/{API_BASE}nodes/{project_private_deleted._id}/'

    def test_return_deleted_public_node(
            self, app, user, title_new, url_project_public_deleted, url_project_private_deleted
    ):
        res = app.get(url_project_public_deleted, expect_errors=True)
        assert res.status_code == 410

    def test_return_deleted_private_node(self, app, user, url_project_private_deleted):
        res = app.get(
            url_project_private_deleted,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 410

    def test_edit_deleted_public_node(self, app, user, title_new, project_public_deleted, url_project_public_deleted):
        res = app.put_json_api(
            url_project_public_deleted,
            params={
                'title': title_new,
                'node_id': project_public_deleted._id,
                'category': project_public_deleted.category
            },
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 410

    def test_edit_deleted_private_node(self, app, user, title_new, project_private_deleted, url_project_private_deleted):
        res = app.put_json_api(
            url_project_private_deleted,
            params={
                'title': title_new,
                'node_id': project_private_deleted._id,
                'category': project_private_deleted.category
            },
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 410

    def test_delete_deleted_public_node(self, app, user, title_new, url_project_public_deleted):
        res = app.delete(
            url_project_public_deleted,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 410

    def test_delete_deleted_private_node(self, app, user, title_new, url_project_private_deleted):
        res = app.delete(
            url_project_private_deleted,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 410
