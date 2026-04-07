import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderExistsMixin
from osf.models import CedarMetadataTemplate
from osf_tests.factories import (
    CollectionProviderFactory,
    BrandFactory,
)


class TestCollectionProviderExists(ProviderExistsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return f'/{API_BASE}providers/collections/fake/'

    @pytest.fixture()
    def provider_url(self, provider):
        return '/{}providers/collections/{}/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def provider_url_two(self, provider_two):
        return '/{}providers/collections/{}/'.format(
            API_BASE, provider_two._id)

    @pytest.fixture()
    def provider_list_url(self, provider):
        return f'/{API_BASE}providers/collections/{provider._id}/submissions/'

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return f'{fake_url}submissions/'

    @pytest.fixture()
    def brand(self):
        return BrandFactory()

    @pytest.fixture()
    def provider_with_brand(self, brand):
        registration_provider = CollectionProviderFactory()
        registration_provider.brand = brand
        registration_provider.save()
        return registration_provider

    @pytest.fixture()
    def provider_url_w_brand(self, provider_with_brand):
        return f'/{API_BASE}providers/collections/{provider_with_brand._id}/'

    def test_registration_provider_with_special_fields(self, app, provider_with_brand, brand, provider_url_w_brand):
        res = app.get(provider_url_w_brand)

        assert res.status_code == 200
        data = res.json['data']

        assert data['relationships']['brand']['data']['id'] == str(brand.id)


@pytest.mark.django_db
class TestCollectionProviderRequiredMetadataTemplate:

    @pytest.fixture()
    def provider(self):
        return CollectionProviderFactory()

    @pytest.fixture()
    def provider_url(self, provider):
        return f'/{API_BASE}providers/collections/{provider._id}/?version=2.20'

    @pytest.fixture()
    def cedar_template(self):
        return CedarMetadataTemplate.objects.create(
            schema_name='Test Schema',
            cedar_id='https://repo.metadatacenter.org/templates/test',
            template_version=1,
            template={},
            active=True,
        )

    def test_required_metadata_template_is_null_by_default(self, app, provider, provider_url):
        res = app.get(provider_url)
        assert res.status_code == 200
        assert res.json['data']['relationships']['required_metadata_template']['data'] is None

    def test_required_metadata_template_when_set(self, app, provider, provider_url, cedar_template):
        from osf.models import AbstractProvider
        AbstractProvider.objects.filter(pk=provider.pk).update(required_metadata_template=cedar_template)

        res = app.get(provider_url)
        assert res.status_code == 200
        rel = res.json['data']['relationships']['required_metadata_template']
        assert rel['data']['id'] == cedar_template._id
        assert rel['data']['type'] == 'cedar-metadata-templates'
