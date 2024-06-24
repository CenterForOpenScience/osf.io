import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    InstitutionFactory,
)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def user_with_institutional_affilation(institution):
    user = AuthUserFactory()
    user.add_or_update_affiliated_institution(institution)
    return user


@pytest.fixture()
def institution():
    return InstitutionFactory()


@pytest.fixture()
def preprint(user_with_institutional_affilation):
    return PreprintFactory(creator=user_with_institutional_affilation)


@pytest.fixture()
def url(preprint):
    return '/{}preprints/{}/institutions/'.format(API_BASE, preprint._id)


@pytest.mark.django_db
class TestPreprintInstitutionsList:

    def test_update_affiliated_institutions_add(self, app, user, user_with_institutional_affilation, preprint, url,
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
            auth=user_with_institutional_affilation.auth
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

    def test_update_affiliated_institutions_remove(self, app, user, user_with_institutional_affilation, preprint, url,
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
            auth=user_with_institutional_affilation.auth
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

    def test_preprint_institutions_list_get(self, app, user, user_with_institutional_affilation, preprint, url,
                                            institution):
        # For testing purposes
        preprint.is_public = False
        preprint.save()

        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.get(url, auth=user_with_institutional_affilation.auth, expect_errors=True)
        assert res.status_code == 200

        assert res.status_code == 200
        assert not res.json['data']

        preprint.add_affiliated_institution(institution, user_with_institutional_affilation)

        res = app.get(url, auth=user_with_institutional_affilation.auth, expect_errors=True)
        assert res.status_code == 200

        assert res.json['data'][0]['id'] == institution._id
        assert res.json['data'][0]['type'] == 'institutions'
        assert url in res.json['links']['self']
