import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderListViewTestBaseMixin
from api.providers.workflows import Workflows


from osf_tests.factories import (
    RegistrationProviderFactory,
)


class TestRegistrationProviderList(ProviderListViewTestBaseMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, request):
        return '/{}providers/registrations/'.format(API_BASE)

    @pytest.fixture
    def moderated_provider(self):
        provider = RegistrationProviderFactory()
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    def test_reviews_workflow_filter(self, app, user, provider_one, moderated_provider, url):
        filter_url = url + '?filter[reviews_workflow]=pre-moderation'
        resp = app.get(filter_url, auth=user.auth)

        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['id'] == moderated_provider._id
