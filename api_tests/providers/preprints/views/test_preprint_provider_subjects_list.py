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


class TestPreprintProviderTaxonomies(ProviderSubjectsMixin):
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


class TestPreprintProviderSubjects(ProviderSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def lawless_url(self, lawless_provider):
        return '/{}providers/preprints/{}/subjects/?page[size]=20&'.format(
            API_BASE, lawless_provider._id)

    @pytest.fixture()
    def ruled_url(self, ruled_provider):
        return '/{}providers/preprints/{}/subjects/?page[size]=20&'.format(
            API_BASE, ruled_provider._id)

    @pytest.fixture()
    def base_url(self, lawless_provider):
        return '/{}providers/preprints/{}/subjects/'.format(
            API_BASE, lawless_provider._id)

    def test_no_rules_with_parents_filter(self, app, lawless_url, subB, subI, subM):
        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

    def test_rules_enforced_with_null_parent_filter(self, app, ruled_url):
        res = app.get(ruled_url + 'filter[parent]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'A' in texts
        assert 'H' in texts
        assert 'L' in texts
        assert 'O' not in texts

    def test_no_rules_with_null_parent_filter(self, app, lawless_url):
        res = app.get(lawless_url + 'filter[parent]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 6

    def test_rules_enforced_with_parents_filter(self, app, ruled_url, subB, subI, subM):
        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subM._id))

    def test_no_rules_with_grandparent_filter(self, app, lawless_url, subA):
        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3

    def test_rules_enforced_with_grandparent_filter(self, app, ruled_url, subA):
        res = app.get(
            ruled_url +
            'filter[parent]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'B' in texts
        assert 'D' in texts
        assert 'C' not in texts


class TestPreprintProviderSpecificSubjectsForDeprecatedEndpoint(ProviderSpecificSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}preprint_providers/{provider_1._id}/taxonomies/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}preprint_providers/{provider_2._id}/taxonomies/?page[size]=15&'


class TestPreprintProviderSpecificTaxonomies(ProviderSpecificSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/preprints/{provider_1._id}/taxonomies/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/preprints/{provider_2._id}/taxonomies/?page[size]=15&'


class TestPreprintProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/preprints/{provider_1._id}/subjects/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/preprints/{provider_2._id}/subjects/?page[size]=15&'


@pytest.mark.django_db
class TestPreprintProviderHighlightedTaxonomies:

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
        return f'/{API_BASE}preprint_providers/{provider._id}/taxonomies/highlighted/'

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/preprints/{provider._id}/taxonomies/highlighted/'

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
class TestPreprintProviderHighlightedSubjects(TestPreprintProviderHighlightedTaxonomies):

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/preprints/{provider._id}/subjects/highlighted/'


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


@pytest.mark.django_db
class TestCustomSubjects(TestCustomTaxonomy):

    @pytest.fixture()
    def url(self):
        return '/{}providers/preprints/{}/subjects/'

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
        assert bepress_res.json['data'][0]['attributes']['taxonomy_name'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['taxonomy_name'] == asdf_provider.share_title
