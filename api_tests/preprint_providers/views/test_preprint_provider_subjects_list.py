import pytest

from api.base.settings.defaults import API_BASE

from osf_tests.factories import SubjectFactory, PreprintProviderFactory


@pytest.mark.django_db
class TestPreprintProviderSubjects:

    @pytest.fixture(autouse=True)
    def subA(self):
        return SubjectFactory(text='A')

    @pytest.fixture(autouse=True)
    def subB(self, subA):
        return SubjectFactory(text='B', parent=subA)

    @pytest.fixture(autouse=True)
    def subC(self, subA):
        return SubjectFactory(text='C', parent=subA)

    @pytest.fixture(autouse=True)
    def subD(self, subA):
        return SubjectFactory(text='D', parent=subA)

    @pytest.fixture(autouse=True)
    def subF(self, subB):
        return SubjectFactory(text='F', parent=subB)

    @pytest.fixture(autouse=True)
    def subG(self, subD):
        return SubjectFactory(text='G', parent=subD)

    @pytest.fixture(autouse=True)
    def subH(self):
        return SubjectFactory(text='H')

    @pytest.fixture(autouse=True)
    def subI(self, subH):
        return SubjectFactory(text='I', parent=subH)

    @pytest.fixture(autouse=True)
    def subJ(self, subI):
        return SubjectFactory(text='J', parent=subI)

    @pytest.fixture(autouse=True)
    def subK(self, subI):
        return SubjectFactory(text='K', parent=subI)

    @pytest.fixture(autouse=True)
    def subL(self):
        return SubjectFactory(text='L')

    @pytest.fixture(autouse=True)
    def subM(self, subL):
        return SubjectFactory(text='M', parent=subL)

    @pytest.fixture(autouse=True)
    def subM(self, subL):
        return SubjectFactory(text='M', parent=subL)

    @pytest.fixture(autouse=True)
    def subE(self, subM):
        return SubjectFactory(text='E', parent=subM)

    @pytest.fixture(autouse=True)
    def subN(self, subM):
        return SubjectFactory(text='N', parent=subM)

    @pytest.fixture(autouse=True)
    def subO(self):
        return SubjectFactory(text='O')

    @pytest.fixture()
    def rules(self, subA, subB, subD, subH, subI, subJ, subL):
        return [
            ([subA._id, subB._id], False),
            ([subA._id, subD._id], True),
            ([subH._id, subI._id, subJ._id], True),
            ([subL._id], True)
        ]
        #  This should allow: A, B, D, G, H, I, J, L, M, N and E
        #  This should not allow: C, F, K, O

    @pytest.fixture()
    def lawless_preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def ruled_preprint_provider(self, rules):
        provider = PreprintProviderFactory()
        provider.subjects_acceptable = rules
        provider.save()
        return provider

    @pytest.fixture()
    def lawless_url(self, lawless_preprint_provider):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(
            API_BASE, lawless_preprint_provider._id)

    @pytest.fixture()
    def lawless_url_generalized(self, lawless_preprint_provider):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(
            API_BASE, lawless_preprint_provider._id)

    @pytest.fixture()
    def ruled_url(self, ruled_preprint_provider):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(
            API_BASE, ruled_preprint_provider._id)

    @pytest.fixture()
    def ruled_url_generalized(self, ruled_preprint_provider):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(
            API_BASE, ruled_preprint_provider._id)

    def test_max_page_size(self, app, lawless_preprint_provider):
        base_url = '/{}preprint_providers/{}/taxonomies/'.format(
            API_BASE, lawless_preprint_provider._id)

        base_url_generalized = base_url = '/{}preprint_providers/{}/taxonomies/'.format(
            API_BASE, lawless_preprint_provider._id)

        res = app.get(base_url)
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 10

        res = app.get(base_url + '?page[size]=150')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 150

        res = app.get(base_url + '?page[size]=2018')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 1000

        res = app.get(base_url_generalized)
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 10

        res = app.get(base_url_generalized + '?page[size]=150')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 150

        res = app.get(base_url_generalized + '?page[size]=2018')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 1000

    def test_no_rules_grabs_all(self, app, lawless_url, lawless_url_generalized):
        res = app.get(lawless_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 15

        res = app.get(lawless_url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 15

    def test_rules_only_grab_acceptable_subjects(self, app, ruled_url, ruled_url_generalized):
        res = app.get(ruled_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 11

        res = app.get(ruled_url_generalized)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 11

    def test_no_rules_with_null_parent_filter(self, app, lawless_url, lawless_url_generalized):
        res = app.get(lawless_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 4

        res = app.get(lawless_url_generalized + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 4

    def test_rules_enforced_with_null_parent_filter(self, app, ruled_url, ruled_url_generalized):
        res = app.get(ruled_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'A' in texts
        assert 'H' in texts
        assert 'L' in texts
        assert 'O' not in texts

        res = app.get(ruled_url_generalized + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'A' in texts
        assert 'H' in texts
        assert 'L' in texts
        assert 'O' not in texts

    def test_no_rules_with_parents_filter(self, app, lawless_url, lawless_url_generalized, subB, subI, subM):
        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url_generalized +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url_generalized +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url_generalized +
            'filter[parents]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

    def test_rules_enforced_with_parents_filter(self, app, ruled_url, ruled_url_generalized, subB, subI, subM):
        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'N' in texts
        assert 'E' in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parents]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parents]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parents]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'N' in texts
        assert 'E' in texts

    def test_no_rules_with_parent_filter(self, app, lawless_url, lawless_url_generalized, subB, subI, subM):
        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url +
            'filter[parent]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url_generalized +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        assert res.json['data'][0]['attributes']['text'] == 'F'

        res = app.get(
            lawless_url_generalized +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

        res = app.get(
            lawless_url_generalized +
            'filter[parent]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2

    def test_rules_enforced_with_parent_filter(self, app, ruled_url, ruled_url_generalized, subB, subI, subM):
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

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'N' in texts
        assert 'E' in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parent]={}'.format(
                subB._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 0
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'F' not in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parent]={}'.format(
                subI._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 1
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'J' in texts
        assert 'K' not in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parent]={}'.format(
                subM._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'N' in texts
        assert 'E' in texts

    def test_no_rules_with_grandparent_filter(self, app, lawless_url, lawless_url_generalized, subA):
        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3

        res = app.get(
            lawless_url_generalized +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3

    def test_rules_enforced_with_grandparent_filter(self, app, ruled_url, ruled_url_generalized, subA):
        res = app.get(
            ruled_url +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'B' in texts
        assert 'D' in texts
        assert 'C' not in texts

        res = app.get(
            ruled_url_generalized +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 2
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'B' in texts
        assert 'D' in texts
        assert 'C' not in texts


@pytest.mark.django_db
class TestPreprintProviderSpecificSubjects:

    @pytest.fixture(autouse=True)
    def provider_1(self):
        return PreprintProviderFactory()

    @pytest.fixture(autouse=True)
    def provider_2(self):
        return PreprintProviderFactory()

    @pytest.fixture(autouse=True)
    def root_subject_1(self, provider_1):
        return SubjectFactory(text='R1', provider=provider_1)

    @pytest.fixture(autouse=True)
    def parent_subject_1(self, provider_1, root_subject_1):
        return SubjectFactory(text='P1', provider=provider_1, parent=root_subject_1)

    @pytest.fixture(autouse=True)
    def child_subject_1(self, provider_1, parent_subject_1):
        return SubjectFactory(text='C1', provider=provider_1, parent=parent_subject_1)

    @pytest.fixture(autouse=True)
    def root_subject_2(self, provider_2):
        return SubjectFactory(text='R2', provider=provider_2)

    @pytest.fixture(autouse=True)
    def parent_subject_2(self, provider_2, root_subject_2):
        return SubjectFactory(text='P2', provider=provider_2, parent=root_subject_2)

    @pytest.fixture(autouse=True)
    def child_subject_2(self, provider_2, parent_subject_2):
        return SubjectFactory(text='C2', provider=provider_2, parent=parent_subject_2)

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_1_generalized(self, provider_1):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)

    @pytest.fixture()
    def url_2_generalized(self, provider_2):
        return '/{}providers/preprints/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)

    def test_mapped_subjects_are_not_shared_list(self, app, url_1, url_2, url_1_generalized, url_2_generalized):
        res_1 = app.get(url_1)
        res_2 = app.get(url_2)

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 3
        assert res_2.json['links']['meta']['total'] == 3

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 6

        res_1 = app.get(url_1_generalized)
        res_2 = app.get(url_2_generalized)

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 3
        assert res_2.json['links']['meta']['total'] == 3

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 6

    def test_mapped_subjects_are_not_shared_filter(self, app, url_1, url_2, url_1_generalized, url_2_generalized, root_subject_1, root_subject_2):
        res_1 = app.get(
            url_1 +
            'filter[parent]={}'.format(
                root_subject_1._id))
        res_2 = app.get(
            url_2 +
            'filter[parent]={}'.format(
                root_subject_2._id))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 1
        assert res_2.json['links']['meta']['total'] == 1

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 2

        res_1 = app.get(
            url_1_generalized +
            'filter[parent]={}'.format(
                root_subject_1._id))
        res_2 = app.get(
            url_2_generalized +
            'filter[parent]={}'.format(
                root_subject_2._id))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 1
        assert res_2.json['links']['meta']['total'] == 1

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) &
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 0

        assert len(set([d['attributes']['text'] for d in res_1.json['data']]) |
                   set([d['attributes']['text'] for d in res_2.json['data']])) \
               == 2

    def test_mapped_subjects_filter_wrong_provider(self, app, url_1, url_2, url_1_generalized, url_2_generalized, root_subject_1, root_subject_2):
        res_1 = app.get(
            url_1 +
            'filter[parent]={}'.format(
                root_subject_2))
        res_2 = app.get(
            url_2 +
            'filter[parent]={}'.format(
                root_subject_1))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 0
        assert res_2.json['links']['meta']['total'] == 0

        res_1 = app.get(
            url_1_generalized +
            'filter[parent]={}'.format(
                root_subject_2))
        res_2 = app.get(
            url_2_generalized +
            'filter[parent]={}'.format(
                root_subject_1))

        assert res_1.status_code == 200
        assert res_2.status_code == 200
        assert res_1.json['links']['meta']['total'] == 0
        assert res_2.json['links']['meta']['total'] == 0


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
    def url(self, provider):
        return '/{}preprint_providers/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def url_generalized(self, provider):
        return '/{}providers/preprints/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)

    def test_mapped_subjects_filter_wrong_provider(self, app, url, url_generalized, subj_aa):
        res = app.get(url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == subj_aa._id

        res = app.get(url_generalized)

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
    def other_subj(self, bepress_subj, asdf_provider):
        return SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=asdf_provider)

    @pytest.fixture()
    def url(self):
        return '/{}preprint_providers/{}/taxonomies/'

    @pytest.fixture()
    def url_generalized(self):
        return '/{}providers/preprints/{}/taxonomies/'

    def test_taxonomy_share_title(self, app, url, url_generalized, osf_provider, asdf_provider, bepress_subj, other_subj):
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

        bepress_res = app.get(
            url_generalized.format(
                API_BASE,
                osf_provider._id))
        asdf_res = app.get(
            url_generalized.format(
                API_BASE,
                asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['share_title'] == osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['share_title'] == asdf_provider.share_title
