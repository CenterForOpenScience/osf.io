import pytest

from osf_tests.factories import (
    AuthUserFactory,
    BrandFactory,
)

from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestBrand:

    @pytest.fixture()
    def brand1(self):
        return BrandFactory()

    @pytest.fixture()
    def brand2(self):
        return BrandFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url_brand_list(self):
        return '/{}brands/'.format(API_BASE)

    @pytest.fixture()
    def url_brand_detail(self, brand1):
        return '/{}brands/{}/'.format(API_BASE, brand1.id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'brands',
                'attributes': {
                    'name': 'Sanders-Taylor',
                    'hero_logo_image': 'https://newton.com/',
                    'topnav_logo_image': 'https://www.mayo-cantrell.org/',
                    'hero_background_image': 'https://whitehead.com/',
                    'primary_color': '#8806ab',
                    'secondary_color': '#dfd126',
                },
                'relationships': {}
            }
        }

    def test_brand_list(self, app, url_brand_list, user, brand1, brand2, payload):
        res = app.get(url_brand_list)

        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 2

        # Ensures that a Brand cannot be created through the API
        res = app.post_json_api(url_brand_list, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_brand_detail(self, app, url_brand_detail, user, brand1, payload):
        res = app.get(url_brand_detail)

        assert res.status_code == 200
        data = res.json['data']
        assert data['id'] == str(brand1.id)
        assert data['attributes']['name'] == brand1.name

        # Ensures that a Brand cannot be edited through the API
        res = app.put_json_api(url_brand_detail, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 405
