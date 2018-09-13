import pytest

from django.test import RequestFactory

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationProviderFactory,
)
from osf.models import RegistrationProvider
from admin_tests.utilities import setup_view, setup_form_view
from admin.registration_providers import views
from admin.registration_providers.forms import RegistrationProviderForm
from admin_tests.mixins.providers import (
    ProcessCustomTaxonomyMixinBase,
    ProviderDisplayMixinBase,
    ProviderListMixinBase,
    CreateProviderMixinBase,
    DeleteProviderMixinBase,
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def req(user):
    req = RequestFactory().get('/fake_path')
    req.user = user
    return req

class TestRegistrationProviderList(ProviderListMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return RegistrationProviderFactory

    @pytest.fixture()
    def provider_class(self):
        return RegistrationProvider

    @pytest.fixture()
    def view(self, req):
        plain_view = views.RegistrationProviderList()
        return setup_view(plain_view, req)


class TestProcessCustomTaxonomy(ProcessCustomTaxonomyMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return RegistrationProviderFactory

    @pytest.fixture()
    def view(self, req):
        plain_view = views.ProcessCustomTaxonomy()
        return setup_view(plain_view, req)


class TestRegistrationProviderDisplay(ProviderDisplayMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return RegistrationProviderFactory

    @pytest.fixture()
    def form_class(self):
        return RegistrationProviderForm

    @pytest.fixture()
    def provider_class(self):
        return RegistrationProvider

    @pytest.fixture()
    def view(self, req, provider):
        plain_view = views.RegistrationProviderDisplay()
        view = setup_view(plain_view, req)
        view.kwargs = {'registration_provider_id': provider.id}
        return view

class TestCreateRegistrationProvider(CreateProviderMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return RegistrationProviderFactory

    @pytest.fixture()
    def view(self, req, provider):
        plain_view = views.CreateRegistrationProvider()
        view = setup_form_view(plain_view, req, form=RegistrationProviderForm())
        view.kwargs = {'registration_provider_id': provider.id}
        return view


class TestDeleteRegistrationProvider(DeleteProviderMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return RegistrationProviderFactory

    @pytest.fixture()
    def view(self, req, provider):
        view = views.DeleteRegistrationProvider()
        view = setup_view(view, req)
        view.kwargs = {'registration_provider_id': provider.id}
        return view
