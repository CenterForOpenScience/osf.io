import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import PreprintFactory, AuthUserFactory, InstitutionFactory
from osf.utils.permissions import READ, WRITE, ADMIN


@pytest.mark.django_db
class TestPreprintInstitutionsRelationship:
    """Test suite for managing preprint institution relationships."""

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution_A(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_B(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_C(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_D(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_E(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_F(self):
        return InstitutionFactory()

    @pytest.fixture()
    def admin_with_institutional_affiliation(self, institution_A, institution_B, institution_C, preprint):
        user = AuthUserFactory()
        preprint.add_contributor(user, permissions=ADMIN)
        user.add_or_update_affiliated_institution(institution_A)
        user.add_or_update_affiliated_institution(institution_B)
        user.add_or_update_affiliated_institution(institution_C)
        return user

    @pytest.fixture()
    def write_user_with_institutional_affiliation(self, institution_B, institution_C, institution_D, preprint):
        user = AuthUserFactory()
        preprint.add_contributor(user, permissions=WRITE)
        user.add_or_update_affiliated_institution(institution_B)
        user.add_or_update_affiliated_institution(institution_C)
        user.add_or_update_affiliated_institution(institution_D)
        return user

    @pytest.fixture()
    def read_user_with_institutional_affiliation(self, institution_C, institution_D, institution_F, preprint):
        user = AuthUserFactory()
        preprint.add_contributor(user, permissions=READ)
        user.add_or_update_affiliated_institution(institution_C)
        user.add_or_update_affiliated_institution(institution_D)
        user.add_or_update_affiliated_institution(institution_F)
        return user

    @pytest.fixture()
    def no_auth_with_institutional_affiliation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.save()
        return user

    @pytest.fixture()
    def admin_without_institutional_affiliation(self, preprint):
        user = AuthUserFactory()
        preprint.add_contributor(user, permissions=ADMIN)
        return user

    @pytest.fixture()
    def institutions(self):
        return [InstitutionFactory() for _ in range(3)]

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def url(self, preprint):
        """Fixture that returns the URL for the preprint-institutions relationship endpoint."""
        return f'/{API_BASE}preprints/{preprint._id}/relationships/institutions/'

    def test_update_affiliated_institutions_add_unauthorized_user(self, app, user, url, institution_A):
        """
        Test that unauthorized users cannot add institutions.
        """
        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_affiliated_institutions_add_read_user(self, app, read_user_with_institutional_affiliation, url, institution_A):
        """
        Test that read users cannot add institutions.
        """
        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=read_user_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_affiliated_institutions_add_write_user(self, app, write_user_with_institutional_affiliation, url, institution_A, institution_B):
        """
        Test that write users cannot add institutions.
        """
        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=write_user_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 403

        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_B._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=write_user_with_institutional_affiliation.auth)
        assert res.status_code == 200

    def test_update_affiliated_institutions_add_admin_without_affiliation(self, app, admin_without_institutional_affiliation, url, institution_A):
        """
        Test that admins without affiliation cannot add institutions.
        """
        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=admin_without_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == f'User needs to be affiliated with {institution_A.name}'

    def test_update_affiliated_institutions_add_admin_with_affiliation(self, app, admin_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that admins with affiliation can add institutions.
        """
        update_institutions_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institutions_payload, auth=admin_with_institutional_affiliation.auth)
        assert res.status_code == 200
        preprint.reload()
        assert institution_A in preprint.affiliated_institutions.all()

        log = preprint.logs.latest()
        assert log.action == 'affiliated_institution_added'
        assert log.params['institution'] == {'id': institution_A._id, 'name': institution_A.name}

    def test_update_affiliated_institutions_remove_unauthorized_user(self, app, user, preprint, url, institution_A):
        """
        Test that unauthorized users cannot remove institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        update_institutions_payload = {'data': []}
        res = app.put_json_api(url, update_institutions_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_affiliated_institutions_remove_read_user(self, app, read_user_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that read users cannot remove institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        update_institutions_payload = {'data': []}
        res = app.put_json_api(url, update_institutions_payload, auth=read_user_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_affiliated_institutions_remove_write_user(self, app, write_user_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that write users cannot remove institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        update_institutions_payload = {'data': []}
        res = app.put_json_api(url, update_institutions_payload, auth=write_user_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 200

    def test_update_affiliated_institutions_remove_admin_without_affiliation(self, app, admin_without_institutional_affiliation, preprint, url, institution_A):
        """
        Test that admins without affiliation can remove institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        update_institutions_payload = {'data': []}
        res = app.put_json_api(url, update_institutions_payload, auth=admin_without_institutional_affiliation.auth)
        assert res.status_code == 200

    def test_update_affiliated_institutions_remove_admin_with_affiliation(self, app, admin_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that admins with affiliation can remove institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        update_institutions_payload = {'data': []}
        res = app.put_json_api(url, update_institutions_payload, auth=admin_with_institutional_affiliation.auth)
        assert res.status_code == 200
        preprint.reload()
        assert institution_A not in preprint.affiliated_institutions.all()

        log = preprint.logs.latest()
        assert log.action == 'affiliated_institution_removed'
        assert log.params['institution'] == {'id': institution_A._id, 'name': institution_A.name}

    def test_preprint_institutions_list_get_unauthenticated(self, app, url):
        """
        Test that unauthenticated users cannot retrieve the list of affiliated institutions for a preprint.
        """
        res = app.get(url, expect_errors=True)
        assert res.status_code == 200

    def test_preprint_institutions_list_get_no_permissions(self, app, user, url):
        """
        Test that users without permissions cannot retrieve the list of affiliated institutions for a preprint.
        """
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_preprint_institutions_list_get_read_user(self, app, read_user_with_institutional_affiliation, preprint, url):
        """
        Test that read users can retrieve the list of affiliated institutions for a preprint.
        """
        preprint.is_public = False
        preprint.save()
        res = app.get(url, auth=read_user_with_institutional_affiliation.auth)
        assert res.status_code == 200
        assert not res.json['data']

    def test_preprint_institutions_list_get_write_user(self, app, write_user_with_institutional_affiliation, preprint, url):
        """
        Test that write users can retrieve the list of affiliated institutions for a preprint.
        """
        preprint.is_public = False
        preprint.save()
        res = app.get(url, auth=write_user_with_institutional_affiliation.auth)
        assert res.status_code == 200
        assert not res.json['data']

    def test_preprint_institutions_list_get_admin_without_affiliation(self, app, admin_without_institutional_affiliation, preprint, url):
        """
        Test that admins without affiliation can retrieve the list of affiliated institutions for a preprint.
        """
        preprint.is_public = False
        preprint.save()
        res = app.get(url, auth=admin_without_institutional_affiliation.auth)
        assert res.status_code == 200
        assert not res.json['data']

    def test_preprint_institutions_list_get_admin_with_affiliation(self, app, admin_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that admins with affiliation can retrieve the list of affiliated institutions for a preprint.
        """
        preprint.add_affiliated_institution(institution_A, admin_with_institutional_affiliation)
        res = app.get(url, auth=admin_with_institutional_affiliation.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == institution_A._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_post_affiliated_institutions(self, app, admin_with_institutional_affiliation, url, institutions):
        """
        Test that POST method is not allowed for affiliated institutions.
        """
        add_institutions_payload = {'data': [{'type': 'institutions', 'id': institution._id} for institution in institutions]}
        res = app.post_json_api(url, add_institutions_payload, auth=admin_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 405

    def test_patch_affiliated_institutions(self, app, admin_with_institutional_affiliation, url, institutions):
        """
        Test that PATCH method is not allowed for affiliated institutions.
        """
        add_institutions_payload = {'data': [{'type': 'institutions', 'id': institution._id} for institution in institutions]}
        res = app.patch_json_api(url, add_institutions_payload, auth=admin_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 405

    def test_delete_affiliated_institution(self, app, admin_with_institutional_affiliation, preprint, url, institution_A):
        """
        Test that DELETE method is not allowed for affiliated institutions.
        """
        preprint.affiliated_institutions.add(institution_A)
        preprint.save()
        res = app.delete_json_api(url, {'data': [{'type': 'institutions', 'id': institution_A._id}]}, auth=admin_with_institutional_affiliation.auth, expect_errors=True)
        assert res.status_code == 405

    def test_add_multiple_institutions_affiliations(self, app, admin_with_institutional_affiliation, preprint, url, institutions):
        """
        Test that admins with multiple affiliations can add them to a preprint.
        """
        for institution in institutions:
            admin_with_institutional_affiliation.add_or_update_affiliated_institution(institution)
        admin_with_institutional_affiliation.save()
        add_institutions_payload = {'data': [{'type': 'institutions', 'id': institution._id} for institution in institutions]}
        res = app.put_json_api(url, add_institutions_payload, auth=admin_with_institutional_affiliation.auth)
        assert res.status_code == 200
        preprint.reload()
        assert preprint.affiliated_institutions.all().count() == 3

    def test_remove_only_institutions_affiliations_that_user_has(self, app, admin_with_institutional_affiliation, preprint, url, institutions, institution_A):
        """
        Test that admins with multiple affiliations only remove their own affiliations, leaving others unchanged.
        """
        preprint.affiliated_institutions.add(*institutions)
        assert preprint.affiliated_institutions.all().count() == 3
        admin_with_institutional_affiliation.add_or_update_affiliated_institution(institutions[0])
        admin_with_institutional_affiliation.add_or_update_affiliated_institution(institutions[1])
        update_institution_payload = {'data': [{'type': 'institutions', 'id': institution_A._id}]}
        res = app.put_json_api(url, update_institution_payload, auth=admin_with_institutional_affiliation.auth)
        assert res.status_code == 200
        assert preprint.affiliated_institutions.all().count() == 2
        assert institution_A in preprint.affiliated_institutions.all()
        assert institutions[2] in preprint.affiliated_institutions.all()
