import pytest

from api.base.settings.defaults import API_BASE
from osf.utils.permissions import WRITE
from osf.utils.workflows import DefaultStates
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
    SubjectFactory,
    PreprintProviderFactory,
)

@pytest.mark.django_db
class TestReviewsPreprintDetailPermissions:

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
    def reviews_provider(self):
        return PreprintProviderFactory(reviews_workflow='pre-moderation')

    @pytest.fixture()
    def unpublished_reviews_preprint(
            self, admin, reviews_provider, subject, public_project, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=reviews_provider,
            subjects=[[subject._id]],
            is_published=False,
            machine_state=DefaultStates.PENDING.value)
        preprint.add_contributor(write_contrib, permissions=WRITE)
        preprint.save()
        return preprint

    @pytest.fixture()
    def unpublished_reviews_initial_preprint(
            self, admin, reviews_provider, subject, public_project):
        return PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunrises.pdf',
            provider=reviews_provider,
            subjects=[[subject._id]],
            is_published=False,
            machine_state=DefaultStates.INITIAL.value)

    @pytest.fixture()
    def private_reviews_preprint(
            self, admin, reviews_provider, subject, private_project, write_contrib):
        preprint = PreprintFactory(
            creator=admin,
            filename='toe_socks_and_sunsets.pdf',
            provider=reviews_provider,
            subjects=[[subject._id]],
            is_published=False,
            is_public=False,
            machine_state=DefaultStates.PENDING.value)
        preprint.add_contributor(write_contrib, permissions=WRITE)
        return preprint

    @pytest.fixture()
    def unpublished_url(self, unpublished_reviews_preprint):
        return '/{}preprints/{}/'.format(
            API_BASE, unpublished_reviews_preprint._id)

    @pytest.fixture()
    def unpublished_initial_url(self, unpublished_reviews_initial_preprint):
        return '/{}preprints/{}/'.format(
            API_BASE, unpublished_reviews_initial_preprint._id)

    @pytest.fixture()
    def private_url(self, private_reviews_preprint):
        return '/{}preprints/{}/'.format(
            API_BASE, private_reviews_preprint._id)

    def test_reviews_preprint_is_published_detail(
            self, app, admin, write_contrib, non_contrib,
            unpublished_reviews_preprint, unpublished_url):

        #   test_unpublished_visible_to_admins
        res = app.get(unpublished_url, auth=admin.auth)
        assert res.json['data']['id'] == unpublished_reviews_preprint._id

    #   test_unpublished_visible_to_write_contribs
        res = app.get(
            unpublished_url,
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200

    #   test_unpublished_invisible_to_non_contribs
        res = app.get(
            unpublished_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unpublished_invisible_to_public
        res = app.get(unpublished_url, expect_errors=True)
        assert res.status_code == 401

    def test_reviews_preprint_initial_detail(
            self, app, admin, write_contrib, non_contrib,
            unpublished_reviews_initial_preprint,
            unpublished_initial_url):

        #   test_unpublished_visible_to_admins
        res = app.get(unpublished_initial_url, auth=admin.auth)
        assert res.json['data']['id'] == unpublished_reviews_initial_preprint._id

    #   test_unpublished_invisible_to_write_contribs
        res = app.get(
            unpublished_initial_url,
            auth=write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unpublished_invisible_to_non_contribs
        res = app.get(
            unpublished_initial_url,
            auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unpublished_invisible_to_public
        res = app.get(unpublished_initial_url, expect_errors=True)
        assert res.status_code == 401

    def test_reviews_preprint_is_public_detail(
            self, app, admin, write_contrib, non_contrib,
            private_reviews_preprint, private_url):

        #   test_private_visible_to_admins
        res = app.get(private_url, auth=admin.auth)
        assert res.json['data']['id'] == private_reviews_preprint._id

    #   test_private_visible_to_write_contribs
        res = app.get(private_url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 200

    #   test_private_invisible_to_non_contribs
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_private_invisible_to_public
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
