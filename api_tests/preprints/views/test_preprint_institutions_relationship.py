import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    InstitutionFactory,
)


@pytest.mark.django_db
class TestPreprintInstitutionsRelationship:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin_with_institutional_affilation(self, institution, preprint):
        user = AuthUserFactory()
        preprint.add_permission(user, 'admin')
        user.add_or_update_affiliated_institution(institution)
        return user

    @pytest.fixture()
    def no_auth_with_institutional_affilation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        return user

    @pytest.fixture()
    def admin_without_institutional_affilation(self, institution, preprint):
        user = AuthUserFactory()
        preprint.add_permission(user, 'admin')
        return user

    @pytest.fixture()
    def institutions(self):
        return [InstitutionFactory() for _ in range(3)]

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/relationships/institutions/'

    def test_update_affiliated_institutions_add(self, app, user, admin_with_institutional_affilation, admin_without_institutional_affilation, preprint, url,
                                                institution):
        update_institutions_payload = {
            'data': [{'type': 'institutions', 'id': institution._id}]
        }

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=admin_without_institutional_affilation.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == f'User needs to be affiliated with {institution.name}'

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=admin_with_institutional_affilation.auth
        )
        assert res.status_code == 200

        preprint.reload()
        assert institution in preprint.affiliated_institutions.all()

        log = preprint.logs.latest()
        assert log.action == 'affiliated_institution_added'
        assert log.params['institution'] == {
            'id': institution._id,
            'name': institution.name
        }

    def test_update_affiliated_institutions_remove(self, app, user, admin_with_institutional_affilation, no_auth_with_institutional_affilation, admin_without_institutional_affilation, preprint, url,
                                                   institution):

        preprint.affiliated_institutions.add(institution)
        preprint.save()

        update_institutions_payload = {
            'data': []
        }

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=no_auth_with_institutional_affilation.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=admin_without_institutional_affilation.auth,
            expect_errors=True
        )
        assert res.status_code == 200  # you can always remove it you are an admin

        res = app.put_json_api(
            url,
            update_institutions_payload,
            auth=admin_with_institutional_affilation.auth
        )
        assert res.status_code == 200

        preprint.reload()
        assert institution not in preprint.affiliated_institutions.all()

        log = preprint.logs.latest()
        assert log.action == 'affiliated_institution_removed'
        assert log.params['institution'] == {
            'id': institution._id,
            'name': institution.name
        }

    def test_preprint_institutions_list_get(self, app, user, admin_with_institutional_affilation, admin_without_institutional_affilation, preprint, url,
                                            institution):
        # For testing purposes
        preprint.is_public = False
        preprint.save()

        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.get(url, auth=admin_without_institutional_affilation.auth, expect_errors=True)
        assert res.status_code == 200

        assert res.status_code == 200
        assert not res.json['data']

        preprint.add_affiliated_institution(institution, admin_with_institutional_affilation)
        res = app.get(url, auth=admin_with_institutional_affilation.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'

    def test_post_affiliated_institutions(self, app, user, admin_with_institutional_affilation, preprint, url,
                                          institutions, institution):
        add_institutions_payload = {
            'data': [{'type': 'institutions', 'id': institution._id} for institution in institutions]
        }

        res = app.post_json_api(
            url,
            add_institutions_payload,
            auth=admin_with_institutional_affilation.auth,
            expect_errors=True
        )
        assert res.status_code == 403  # Adding affilations you don't have

        add_institutions_payload = {
            'data': [{'type': 'institutions', 'id': institution._id}],
        }

        res = app.post_json_api(
            url,
            add_institutions_payload,
            auth=admin_with_institutional_affilation.auth
        )
        assert res.status_code == 201

        preprint.reload()
        assert preprint.affiliated_institutions.all()[0] == institution

    def test_delete_affiliated_institution(self, app, user, admin_with_institutional_affilation, admin_without_institutional_affilation, preprint, url,
                                           institution):

        preprint.affiliated_institutions.add(institution)
        preprint.save()

        res = app.delete_json_api(
            url,
            {'data': [{'type': 'institutions', 'id': institution._id}]},
            auth=admin_with_institutional_affilation.auth
        )
        assert res.status_code == 204

        preprint.reload()
        assert institution not in preprint.affiliated_institutions.all()

    def test_complex_institutional_affiliations(self, app, user, admin_with_institutional_affilation, admin_without_institutional_affilation, preprint, url,
                                                institutions):
        # Add multiple institutions
        add_institutions_payload = {
            'data': [{'type': 'institutions', 'id': institution._id} for institution in institutions]
        }

        res = app.post_json_api(
            url,
            add_institutions_payload,
            auth=admin_with_institutional_affilation.auth,
            expect_errors=True
        )
        assert res.status_code == 403  # Adding affilations you don't have

        preprint.reload()
        assert len(preprint.affiliated_institutions.all()) == 0

        # add one institution
        remove_institution_payload = {
            'data': [{'type': 'institutions', 'id': institutions[0]._id}]
        }

        res = app.put_json_api(
            url,
            remove_institution_payload,
            auth=admin_with_institutional_affilation.auth
        )
        assert res.status_code == 201

        preprint.reload()
        assert len(preprint.affiliated_institutions.all()) == 1
        assert len(preprint.affiliated_institutions.all()) == 1

        # Check user affiliations
        other_user = AuthUserFactory()
        other_user.add_or_update_affiliated_institution(institutions[1])
        other_user.add_or_update_affiliated_institution(institutions[2])

        res = app.get(url, auth=other_user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
