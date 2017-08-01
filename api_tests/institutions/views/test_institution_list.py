import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import InstitutionFactory

@pytest.mark.django_db
class TestInstitutionList:

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_two(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_institution(self):
        return '/{}institutions/'.format(API_BASE)

    def test_return_all_institutions(self, app, institution_one, institution_two, url_institution):
        res_institutions = app.get(url_institution)
        data_institutions = res_institutions.json['data']

        assert res_institutions.status_code == 200

        ids = [each['id'] for each in data_institutions]
        assert len(data_institutions) == 2
        assert res_institutions.json['links']['meta']['per_page'] == 1000

        assert institution_one._id in ids
        assert institution_two._id in ids

    def test_does_not_return_deleted_institution(self, app, institution_one, institution_two, url_institution):
        institution_one.is_deleted = True
        institution_one.save()

        res = app.get(url_institution)
        assert res.status_code == 200

        ids = [each['id'] for each in res.json['data']]
        assert len(res.json['data']) == 1
        assert institution_one._id not in ids
        assert institution_two._id in ids
