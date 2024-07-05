import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    InstitutionFactory,
)
from osf.utils import permissions as osf_permissions


@pytest.mark.django_db
class TestPrivatePreprintInstitutionsList:

    @pytest.fixture()
    def url(self, private_preprint):
        return f'/{API_BASE}preprints/{private_preprint._id}/institutions/'

    @pytest.fixture()
    def invalid_url(self):
        return f'/{API_BASE}preprints/invalid_id/institutions/'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_preprint(self):
        preprint = PreprintFactory()
        preprint.is_public = False
        preprint.save()
        return preprint

    @pytest.fixture()
    def read_contrib(self, private_preprint):
        user = AuthUserFactory()
        private_preprint.add_permission(user, osf_permissions.READ)
        return user

    @pytest.fixture()
    def write_contrib(self, private_preprint):
        user = AuthUserFactory()
        private_preprint.add_permission(user, osf_permissions.WRITE)
        return user

    @pytest.fixture()
    def admin_contrib(self, private_preprint):
        user = AuthUserFactory()
        private_preprint.add_permission(user, osf_permissions.ADMIN)
        return user

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    def test_preprint_institutions_no_auth(self, app, url):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    def test_preprint_institutions_unauth(self, app, url, user, private_preprint):
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_preprint_institutions_read(self, app, url, read_contrib, private_preprint, institution):

        res = app.get(url, auth=read_contrib.auth)
        assert res.status_code == 200
        assert not res.json['data']

        private_preprint.affiliated_institutions.add(institution)
        res = app.get(url, auth=read_contrib.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_preprint_institutions_write(self, app, url, write_contrib, private_preprint, institution):

        res = app.get(url, auth=write_contrib.auth)
        assert res.status_code == 200

        assert not res.json['data']

        private_preprint.affiliated_institutions.add(institution)
        res = app.get(url, auth=write_contrib.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_preprint_institutions_admin(self, app, url, admin_contrib, private_preprint, institution):

        res = app.get(url, auth=admin_contrib.auth)
        assert res.status_code == 200

        assert not res.json['data']

        private_preprint.affiliated_institutions.add(institution)
        res = app.get(url, auth=admin_contrib.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_invalid_preprint_id(self, app, invalid_url):
        res = app.get(invalid_url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestPublicPreprintInstitutionsList:

    @pytest.fixture()
    def url(self, public_preprint):
        return f'/{API_BASE}preprints/{public_preprint._id}/institutions/'

    @pytest.fixture()
    def invalid_url(self):
        return f'/{API_BASE}preprints/invalid_id/institutions/'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def public_preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def read_contrib(self, public_preprint):
        user = AuthUserFactory()
        public_preprint.add_permission(user, osf_permissions.READ)
        return user

    def test_preprint_institutions_no_auth(self, app, url):
        res = app.get(url)
        assert res.status_code == 200

    def test_preprint_institutions_unauth(self, app, url, user):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

    def test_preprint_institutions_read(self, app, url, read_contrib, public_preprint, institution):

        res = app.get(url, auth=read_contrib.auth)
        assert res.status_code == 200
        assert not res.json['data']

        public_preprint.affiliated_institutions.add(institution)
        res = app.get(url, auth=read_contrib.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_invalid_preprint_id(self, app, invalid_url):
        res = app.get(invalid_url, expect_errors=True)
        assert res.status_code == 404
