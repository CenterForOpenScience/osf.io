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
from django.utils import timezone

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
            provider=provider,
            is_published=False,
            machine_state='initial'
        )

    @pytest.fixture()
    def private_preprint(self, admin, provider, subject, private_project, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            provider=provider,
            is_published=True,
            is_public=False,
            machine_state='accepted'
        )
        preprint.add_contributor(write_contrib, permissions=WRITE)
        preprint.save()
        return preprint

    @pytest.fixture()
    def published_preprint(self, admin, provider, subject, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            provider=provider,
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
            provider=provider,
            project=private_project,
            is_published=False,
            is_public=False,
            machine_state='initial'
        )

    @pytest.fixture()
    def abandoned_public_preprint(self, admin, provider, subject, public_project):
        return PreprintFactory(
            creator=admin,
            provider=provider,
            project=public_project,
            is_published=False,
            is_public=True,
            machine_state='initial'
        )

    @pytest.fixture()
    def deleted_preprint(self, admin, provider, subject, public_project):
        preprint = PreprintFactory(
            creator=admin,
            provider=provider,
            project=public_project,
            is_published=False,
            is_public=False,
            machine_state='initial',
        )
        preprint.deleted = timezone.now()
        preprint.save()
        return preprint

    def test_gets_preprint_drafts(self, app, admin, abandoned_public_preprint, abandoned_private_preprint, published_preprint):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=admin.auth
        )
        assert res.status_code == 200

        ids = [each['id'] for each in res.json['data']]
        assert abandoned_public_preprint._id in ids
        assert abandoned_private_preprint._id in ids
        assert published_preprint._id not in ids

    def test_anonymous_gets_401(self, app, admin):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            expect_errors=True
        )
        assert res.status_code == 401

    def test_get_preprints_non_contrib_gets_403(self, app, admin, non_contrib, abandoned_public_preprint, abandoned_private_preprint):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_get_projects_logged_in_as_write_user(self, app, admin, write_contrib, abandoned_public_preprint):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_deleted_drafts_excluded(self, app, admin, abandoned_public_preprint, abandoned_private_preprint, published_preprint, deleted_preprint):
        res = app.get(
            f'/{API_BASE}users/{admin._id}/draft_preprints/',
            auth=admin.auth
        )
        assert res.status_code == 200

        ids = [each['id'] for each in res.json['data']]
        assert abandoned_public_preprint._id in ids
        assert abandoned_private_preprint._id in ids
        assert published_preprint._id not in ids
        assert deleted_preprint._id not in ids  # Make sure deleted preprints are not listed
