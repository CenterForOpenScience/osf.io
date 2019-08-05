import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    RegionFactory,
    InstitutionFactory
)


@pytest.mark.django_db
class TestRegionList:
    @pytest.fixture()
    def region(self):
        return RegionFactory(name='Frankfort', _id='eu-central-1')

    @pytest.fixture()
    def regions_url(self):
        return '/{}regions/'.format(
            API_BASE)

    @pytest.fixture()
    def user(self):
        usr = AuthUserFactory()
        inst = InstitutionFactory()
        usr.affiliated_institutions.add(inst)
        return usr

    def test_region_list(self, app, region, regions_url, user):
        # test length and not auth
        res = app.get(regions_url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(data) == 1

    def test_custom_storage_region_list(self, app, region, regions_url, user):
        RegionFactory(_id=user.affiliated_institutions.first()._id)
        res = app.get(regions_url, auth=user.auth)
        data = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(data) == 1
