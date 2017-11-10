import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
)


@pytest.mark.django_db
class TestPreprintProviderList:

    @pytest.fixture()
    def url(self):
        return '/{}preprint_providers/?version=2.2&'.format(API_BASE)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory(name='Sockarxiv')

    @pytest.fixture()
    def provider_two(self):
        provider = PreprintProviderFactory(name='Spotarxiv')
        provider.allow_submissions = False
        provider.domain = 'https://www.spotarxiv.com'
        provider.description = 'spots not dots'
        provider.domain_redirect_enabled = True
        provider._id = 'spot'
        provider.share_publish_type = 'Thesis'
        provider.save()
        return provider


    def test_preprint_provider_list(self, app, url, user, provider_one, provider_two):
        # Test length and not auth
        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 2

        # Test length and auth
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2

    @pytest.mark.parametrize('filter_type,filter_value', [
        ('allow_submissions', True),
        ('description', 'spots%20not%20dots'),
        ('domain', 'https://www.spotarxiv.com'),
        ('domain_redirect_enabled', True),
        ('id', 'spot'),
        ('name', 'Spotarxiv'),
        ('share_publish_type', 'Thesis'),
    ])
    def test_preprint_provider_list_filtering(self, filter_type, filter_value, app, url, provider_one, provider_two):
        res = app.get('{}filter[{}]={}'.format(url, filter_type, filter_value))
        assert res.status_code == 200
        assert len(res.json['data']) == 1
