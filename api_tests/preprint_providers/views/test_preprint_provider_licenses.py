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
    def license1(self, licenses):
        return licenses[0]

    @pytest.fixture()
    def license2(self, licenses):
        return licenses[1]

    @pytest.fixture()
    def license3(self, licenses):
        return licenses[2]

    @pytest.fixture()
    def url(self, provider):
        return '/{}preprint_providers/{}/licenses/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def url_generalized(self, provider):
        return '/{}providers/preprints/{}/licenses/'.format(
            API_BASE, provider._id)

    def test_preprint_provider_has_no_acceptable_licenses_and_no_default(self, app, provider, licenses, url):
        provider.licenses_acceptable = []
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)

    def test_preprint_provider_has_a_default_license_but_no_acceptable_licenses(self, app, provider, licenses, license2, url):
        provider.licenses_acceptable = []
        provider.default_license = license2
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)
        assert license2._id == res.json['data'][0]['id']

    def test_prerint_provider_has_acceptable_licenses_but_no_default(self, app, provider, licenses, license1, license2, license3, url):
        provider.licenses_acceptable.add(license1, license2)
        provider.default_license = None
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license1._id in license_ids
        assert license2._id in license_ids
        assert license3._id not in license_ids

    def test_preprint_provider_has_both_acceptable_and_default_licenses(self, app, provider, licenses, license1, license2, license3, url):
        provider.licenses_acceptable.add(license1, license3)
        provider.default_license = license3
        provider.save()
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license1._id in license_ids
        assert license3._id in license_ids
        assert license2._id not in license_ids

        assert license3._id == license_ids[0]

    def test_preprint_provider_has_no_acceptable_licenses_and_no_default_for_generalized_endpoint(self, app, provider, licenses, url_generalized):
        provider.licenses_acceptable = []
        provider.default_license = None
        provider.save()
        res = app.get(url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)

    def test_preprint_provider_has_a_default_license_but_no_acceptable_licenses_for_generalized_endpoint(self, app, provider, licenses, license2, url_generalized):
        provider.licenses_acceptable = []
        provider.default_license = license2
        provider.save()
        res = app.get(url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == len(licenses)
        assert license2._id == res.json['data'][0]['id']

    def test_prerint_provider_has_acceptable_licenses_but_no_default_for_generalized_endpoint(self, app, provider, licenses, license1, license2, license3, url_generalized):
        provider.licenses_acceptable.add(license1, license2)
        provider.default_license = None
        provider.save()
        res = app.get(url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license1._id in license_ids
        assert license2._id in license_ids
        assert license3._id not in license_ids

    def test_preprint_provider_has_both_acceptable_and_default_licenses_for_generalized_endpoint(self, app, provider, licenses, license1, license2, license3, url_generalized):
        provider.licenses_acceptable.add(license1, license3)
        provider.default_license = license3
        provider.save()
        res = app.get(url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        license_ids = [item['id'] for item in res.json['data']]
        assert license1._id in license_ids
        assert license3._id in license_ids
        assert license2._id not in license_ids

        assert license3._id == license_ids[0]
