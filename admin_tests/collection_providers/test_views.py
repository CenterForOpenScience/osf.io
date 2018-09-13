import pytest

from django.test import RequestFactory

from osf_tests.factories import (
    AuthUserFactory,
    CollectionProviderFactory
)
from osf.models import CollectionProvider
from admin_tests.utilities import setup_view, setup_form_view
from admin.collection_providers import views
from admin.collection_providers.forms import CollectionProviderForm
from admin_tests.mixins.providers import (
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

class TestCollectionProviderList(ProviderListMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return CollectionProviderFactory

    @pytest.fixture()
    def provider_class(self):
        return CollectionProvider

    @pytest.fixture()
    def view(self, req):
        plain_view = views.CollectionProviderList()
        return setup_view(plain_view, req)


class TestCollectionProviderDisplay(ProviderDisplayMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return CollectionProviderFactory

    @pytest.fixture()
    def form_class(self):
        return CollectionProviderForm

    @pytest.fixture()
    def provider_class(self):
        return CollectionProvider

    @pytest.fixture()
    def view(self, req, provider):
        plain_view = views.CollectionProviderDisplay()
        view = setup_view(plain_view, req)
        view.kwargs = {'collection_provider_id': provider.id}
        return view


class TestCreateCollectionProvider(CreateProviderMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return CollectionProviderFactory

    @pytest.fixture()
    def view(self, req, provider):
        plain_view = views.CreateCollectionProvider()
        view = setup_form_view(plain_view, req, form=CollectionProviderForm())
        view.kwargs = {'collection_provider_id': provider.id}
        return view


class TestDeleteCollectionProvider(DeleteProviderMixinBase):

    @pytest.fixture()
    def provider_factory(self):
        return CollectionProviderFactory

    @pytest.fixture()
    def view(self, req, provider):
        view = views.DeleteCollectionProvider()
        view = setup_view(view, req)
        view.kwargs = {'collection_provider_id': provider.id}
        return view
