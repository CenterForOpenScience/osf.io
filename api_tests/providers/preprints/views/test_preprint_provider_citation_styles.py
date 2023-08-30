import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import PreprintProviderFactory

@pytest.mark.django_db
class TestPreprintProviderCitationStyles:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/preprints/{provider._id}/citation_styles/'

    def test_retrieve_citation_styles_with_valid_provider_id(self, app, provider, url):
        res = app.get(url)

        assert res.status_code == 200

    def test_retrieve_citation_styles_with_invalid_provider_id(self, app):
        invalid_url = f'/{API_BASE}providers/preprints/invalid_id/citation_styles/'
        res = app.get(invalid_url, expect_errors=True)

        assert res.status_code == 404
