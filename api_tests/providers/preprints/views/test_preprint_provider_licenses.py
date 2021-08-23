import pytest

from api.base.settings.defaults import API_BASE

from osf.models.licenses import NodeLicense
from osf_tests.factories import PreprintProviderFactory

@pytest.mark.django_db
class TestPreprintProviderLicenses:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def licenses(self):
        return NodeLicense.objects.all()

    @pytest.fixture()
    def license_one(self, licenses):
        return licenses[0]

    @pytest.fixture()
    def license_two(self, licenses):
        return licenses[1]

    @pytest.fixture()
    def license_three(self, licenses):
        return licenses[2]

    @pytest.fixture(params=['/{}preprint_providers/{}/licenses/', '/{}providers/preprints/{}/licenses/'])
    def url(self, provider, request):
        url = request.param
        return url.format(
            API_BASE, provider._id)

    def test_preprint_provider_has_no_acceptable_licenses_and_no_default(self, app, provider, licenses, url):
        provider.licenses_acceptable.clear()
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)

    def test_preprint_provider_has_a_default_license_but_no_acceptable_licenses(self, app, provider, licenses, license_two, url):
        provider.licenses_acceptable.clear()
        provider.default_license = license_two
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)
        assert license_two._id in [item['id'] for item in res.json['data']]

    def test_prerint_provider_has_acceptable_licenses_but_no_default(self, app, provider, licenses, license_one, license_two, license_three, url):
        provider.licenses_acceptable.add(license_one, license_two)
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license_one._id in license_ids
        assert license_two._id in license_ids
        assert license_three._id not in license_ids

    def test_preprint_provider_has_both_acceptable_and_default_licenses(self, app, provider, licenses, license_one, license_two, license_three, url):
        provider.licenses_acceptable.add(license_one, license_three)
        provider.default_license = license_three
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license_one._id in license_ids
        assert license_three._id in license_ids
        assert license_two._id not in license_ids
