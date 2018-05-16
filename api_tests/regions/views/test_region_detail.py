import pytest

from api.base.settings.defaults import API_BASE
from addons.osfstorage.tests.factories import RegionFactory
from osf_tests.factories import (
    AuthUserFactory,
)

@pytest.mark.django_db
class TestRegionDetail:

    @pytest.fixture()
    def region(self):
        return RegionFactory(name='Frankfort', _id='eu-central-1')

    @pytest.fixture()
    def bad_url(self):
        return '/{}regions/blah/'.format(API_BASE)

    @pytest.fixture()
    def region_url(self, region):
        return '/{}regions/{}/'.format(
            API_BASE, region._id)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    def test_region_detail(self, app, region_url, user):
        # test not auth
        detail_res = app.get(region_url)
        assert detail_res.status_code == 200
        assert detail_res.json['data']['attributes']['name'] == 'Frankfort'
        assert detail_res.json['data']['id'] == 'eu-central-1'

        # test auth
        detail_res = app.get(region_url, auth=user.auth)
        assert detail_res.status_code == 200

    def test_region_not_found(self, app, bad_url):
        detail_res = app.get(bad_url, expect_errors=True)
        assert detail_res.status_code == 404
