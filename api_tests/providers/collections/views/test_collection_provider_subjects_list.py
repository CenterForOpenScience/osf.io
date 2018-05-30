import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderSpecificSubjectsMixin

from osf_tests.factories import SubjectFactory, CollectionProviderFactory


class TestProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}providers/collections/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}providers/collections/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)


@pytest.mark.django_db
class TestProviderHighlightedSubjects:

    @pytest.fixture()
    def provider(self):
        return CollectionProviderFactory()

    @pytest.fixture()
    def subj_a(self, provider):
        return SubjectFactory(provider=provider, text='A')

    @pytest.fixture()
    def subj_aa(self, provider, subj_a):
        return SubjectFactory(provider=provider, text='AA', parent=subj_a, highlighted=True)

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/collections/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)

    def test_mapped_subjects_filter_wrong_provider(self, app, url, subj_aa):
        res = app.get(url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == subj_aa._id


@pytest.mark.django_db
class TestCustomTaxonomy:

    @pytest.fixture()
    def osf_provider(self):
        return CollectionProviderFactory(_id='osf')

    @pytest.fixture()
    def asdf_provider(self):
        return CollectionProviderFactory(_id='asdf')

    @pytest.fixture()
    def bepress_subj(self, osf_provider):
        return SubjectFactory(text='BePress Text', provider=osf_provider)

    @pytest.fixture()
    def other_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def url(self):
        return '/{}providers/collections/{}/taxonomies/'

    def test_taxonomy_share_title(self, app, url, osf_provider, asdf_provider, bepress_subj, other_subj):
        bepress_res = app.get(
            url.format(
                API_BASE,
                osf_provider._id))
        asdf_res = app.get(
            url.format(
                API_BASE,
                asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['share_title'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['share_title'] == asdf_provider.share_title
