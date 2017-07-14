import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import PreprintProviderFactory

@pytest.mark.django_db
class TestPreprintProviderExists:

    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def fake_url(self):
        return '/{}preprint_providers/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(API_BASE, preprint_provider._id)

    def test_preprint_provider_exists(self, app, provider_url, fake_url):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        preprints_res = app.get('{}preprints/'.format(provider_url))
        assert preprints_res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

    #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get('{}licenses/'.format(fake_url), expect_errors=True)
        assert licenses_res.status_code == 404

        preprints_res = app.get('{}preprints/'.format(fake_url), expect_errors=True)
        assert preprints_res.status_code == 404

        taxonomies_res = app.get('{}taxonomies/'.format(fake_url), expect_errors=True)
        assert taxonomies_res.status_code == 404
