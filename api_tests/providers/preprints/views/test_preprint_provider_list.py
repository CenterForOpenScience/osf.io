import mock
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
)

@pytest.fixture(params=['/{}preprint_providers/?version=2.2&', '/{}providers/preprints/?version=2.2&'])
def url(request):
    url = (request.param)
    return url.format(API_BASE)

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def provider_one():
    return PreprintProviderFactory(_id='sock', name='Sockarxiv')

@pytest.fixture()
def provider_two():
    provider = PreprintProviderFactory(name='Spotarxiv')
    provider.allow_submissions = False
    provider.domain = 'https://www.spotarxiv.com'
    provider.description = 'spots not dots'
    provider.domain_redirect_enabled = True
    provider._id = 'spot'
    provider.share_publish_type = 'Thesis'
    provider.save()
    return provider

@pytest.mark.django_db
class TestPreprintProviderList:

    def test_preprint_provider_list(
            self, app, url, user, provider_one, provider_two):
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
    def test_preprint_provider_list_filtering(
            self, filter_type, filter_value, app, url,
            provider_one, provider_two):
        res = app.get('{}filter[{}]={}'.format(
            url, filter_type, filter_value))
        assert res.status_code == 200
        assert len(res.json['data']) == 1


@pytest.mark.django_db
class TestPreprintProviderListWithMetrics:

    def test_preprint_provider_list_with_metrics(self, app, url, provider_one, provider_two, settings):
        settings.ENABLE_ELASTICSEARCH_METRICS = True
        provider_one.downloads = 41
        provider_two.downloads = 42
        with mock.patch('api.preprints.views.PreprintDownload.get_top_by_count') as mock_get_top_by_count:
            mock_get_top_by_count.return_value = [provider_one, provider_two]
            res = app.get(url + 'metrics[downloads]=total')

        assert res.status_code == 200

        provider_2_data = res.json['data'][0]
        provider_2_data['meta']['metrics']['downloads'] == 42

        provider_1_data = res.json['data'][1]
        provider_1_data['meta']['metrics']['downloads'] == 41
