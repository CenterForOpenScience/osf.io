import pytest
from osf.utils.permissions import WRITE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
    PreprintProviderFactory,
)
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestPreprintDraftList:

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, admin):
        return ProjectFactory(creator=admin, is_public=True)

    @pytest.fixture()
    def private_project(self, admin):
        return ProjectFactory(creator=admin, is_public=False)

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def unpublished_preprint(self, admin, provider, subject, public_project):
        return PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=False,
            machine_state='initial'
        )

    @pytest.fixture()
    def private_preprint(self, admin, provider, subject, private_project, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=True,
            is_public=False,
            machine_state='accepted'
        )
        preprint.add_contributor(write_contrib, permissions=WRITE)
        preprint.is_public = False
        preprint.save()
        return preprint

    @pytest.fixture()
    def published_preprint(self, admin, provider, subject, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            is_published=True,
            is_public=True,
            machine_state='accepted'
        )
        preprint.add_contributor(write_contrib, permissions=WRITE)
        return preprint

    @pytest.fixture()
    def abandoned_private_preprint(self, admin, provider, subject, private_project):
        return PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            project=private_project,
            is_published=False,
            is_public=False,
            machine_state='initial'
        )

    @pytest.fixture()
    def abandoned_public_preprint(self, admin, provider, subject, public_project):
        return PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=provider,
            subjects=[[subject._id]],
            project=public_project,
            is_published=False,
            is_public=True,
            machine_state='initial'
        )

    def test_authorized_in_gets_200(self, app, admin, preprint):
        url = f'/{API_BASE}users/{admin._id}/draft_preprints/'
        res = app.get(url, auth=admin.auth)
        assert res.status_code == 200

    def test_anonymous_gets_401(self, app, admin):
        url = f'/{API_BASE}users/{admin._id}/draft_preprints/'
        res = app.get(url)
        assert res.status_code == 401

    def test_get_preprints_403(self, app, admin, non_contrib, preprint):
        url = f'/{API_BASE}users/{admin._id}/draft_preprints/'
        res = app.get(url, auth=non_contrib.auth)
        assert res.status_code == 401

    def test_get_projects_not_logged_in(self, app, preprint, admin, project_public, project_private):
        res = app.get(f'/{API_BASE}users/{admin._id}/draft_preprints/')
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert preprint._id in ids
        assert project_public._id not in ids
        assert project_private._id not in ids

    def test_get_projects_logged_in_as_different_user(self, app, admin, write_contrib, preprint, project_public, project_private):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=write_contrib.auth
        )
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert preprint._id in ids
        assert project_public._id not in ids
        assert project_private._id not in ids

    def test_abandoned_preprint_in_results(self, app, admin, abandoned_public_preprint, abandoned_private_preprint, published_preprint):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=admin.auth
        )
        actual = [result['id'] for result in res.json['data']]
        assert abandoned_public_preprint._id in actual
