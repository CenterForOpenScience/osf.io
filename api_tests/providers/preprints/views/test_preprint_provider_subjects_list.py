import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderSubjectsMixin, ProviderSpecificSubjectsMixin

from osf_tests.factories import SubjectFactory, PreprintProviderFactory


class TestPreprintProviderSubjectsForDeprecatedEndpoint(ProviderSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def lawless_url(self, lawless_provider):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=20&'.format(
            API_BASE, lawless_provider._id)

    @pytest.fixture()
    def ruled_url(self, ruled_provider):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=20&'.format(
            API_BASE, ruled_provider._id)

    @pytest.fixture()
    def base_url(self, lawless_provider):
        return '/{}preprint_providers/{}/taxonomies/'.format(
            API_BASE, lawless_provider._id)


class TestPreprintProviderSubjects(ProviderSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def lawless_url(self, lawless_provider):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=20&'.format(
            API_BASE, lawless_provider._id)

    @pytest.fixture()
    def ruled_url(self, ruled_provider):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=20&'.format(
            API_BASE, ruled_provider._id)

    @pytest.fixture()
    def base_url(self, lawless_provider):
        return '/{}providers/preprints/{}/taxonomies/'.format(
            API_BASE, lawless_provider._id)


class TestPreprintProviderSpecificSubjectsForDeprecatedEndpoint(ProviderSpecificSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)


class TestPreprintProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)


@pytest.mark.django_db
class TestPreprintProviderHighlightedSubjects:

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def subj_a(self, provider):
        return SubjectFactory(provider=provider, text='A')

    @pytest.fixture()
    def subj_aa(self, provider, subj_a):
        return SubjectFactory(provider=provider, text='AA', parent=subj_a, highlighted=True)

    @pytest.fixture()
    def other_subj(self, provider):
        return SubjectFactory(text='Other Text', provider=provider, highlighted=True)

    @pytest.fixture()
    def z_subj(self, provider):
        return SubjectFactory(text='Zzz Text', provider=provider, highlighted=True)

    @pytest.fixture()
    def url_deprecated(self, provider):
        return '/{}preprint_providers/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/preprints/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)

    def test_taxonomy_other_ordering(self, app, url, provider, subj_a, subj_aa, other_subj, z_subj):
        res = app.get(url)
        assert len(res.json['data']) == 3
        assert res.json['data'][0]['id'] == subj_aa._id
        assert res.json['data'][1]['id'] == z_subj._id
        assert res.json['data'][2]['id'] == other_subj._id

    def test_mapped_subjects_filter_wrong_provider(self, app, url_deprecated, url, subj_aa):
        res = app.get(url_deprecated)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == subj_aa._id

        res = app.get(url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == subj_aa._id


@pytest.mark.django_db
class TestCustomTaxonomy:

    @pytest.fixture()
    def osf_provider(self):
        return PreprintProviderFactory(_id='osf', share_title='bepress')

    @pytest.fixture()
    def asdf_provider(self):
        return PreprintProviderFactory(_id='asdf', share_title='ASDF')

    @pytest.fixture()
    def bepress_subj(self, osf_provider):
        return SubjectFactory(text='BePress Text', provider=osf_provider)

    @pytest.fixture()
    def a_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Aaa Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def other_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def z_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Zzz Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def url_deprecated(self):
        return '/{}preprint_providers/{}/taxonomies/'

    @pytest.fixture()
    def url(self):
        return '/{}providers/preprints/{}/taxonomies/'

    def test_taxonomy_other_ordering(self, app, url, asdf_provider, a_subj, other_subj, z_subj):
        res = app.get(url.format(API_BASE, asdf_provider._id))
        assert len(res.json['data']) == 3
        assert res.json['data'][0]['id'] == a_subj._id
        assert res.json['data'][1]['id'] == z_subj._id
        assert res.json['data'][2]['id'] == other_subj._id

    def test_taxonomy_share_title(self, app, url_deprecated, url, osf_provider, asdf_provider, bepress_subj, other_subj):
        bepress_res = app.get(
            url_deprecated.format(
                API_BASE,
                osf_provider._id))
        asdf_res = app.get(
            url_deprecated.format(
                API_BASE,
                asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['share_title'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['share_title'] == asdf_provider.share_title

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
