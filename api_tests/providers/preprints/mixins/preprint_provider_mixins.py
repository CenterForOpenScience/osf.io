import pytest
from osf_tests.factories import SubjectFactory, PreprintProviderFactory
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestPreprintProviderExistsMixin(object):
    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    @pytest.fixture()
    def fake_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_url_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_preprints_list_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_preprints_list_url_fake(self):
        raise NotImplementedError

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def preprint_provider_two(self):
        return PreprintProviderFactory()

    def test_preprint_provider_exists(self, app, provider_url, fake_url, provider_preprints_list_url, provider_preprints_list_url_fake):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        preprints_res = app.get(provider_preprints_list_url)
        assert preprints_res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

        #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get(
            '{}licenses/'.format(fake_url),
            expect_errors=True)
        assert licenses_res.status_code == 404

        preprints_res = app.get(
            provider_preprints_list_url_fake,
            expect_errors=True)
        assert preprints_res.status_code == 404

        taxonomies_res = app.get(
            '{}taxonomies/'.format(fake_url),
            expect_errors=True)
        assert taxonomies_res.status_code == 404

    def test_has_highlighted_subjects_flag(
            self, app, preprint_provider,
            preprint_provider_two, provider_url, provider_url_two):
        SubjectFactory(
            provider=preprint_provider,
            text='A', highlighted=True)
        SubjectFactory(provider=preprint_provider_two, text='B')

        res = app.get(provider_url)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is True

        provider_url_two = '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider_two._id)
        res = app.get(provider_url_two)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is False


@pytest.mark.django_db
class TestPreprintProviderSubjectsMixin(object):
    '''
    Subject Hierarchy
    +-----------------------------+
    |                             |
    |      +-------->B+----->F    |
    |      |                      |
    |  A+----------->C            |
    |      |                      |
    |      +-------->D+----->G    |
    |                             |
    |  H+------>I+----->J         |
    |            |                |
    |            +----->K         |
    |                             |
    |  L+------>M+----->N         |
    |            |                |
    |            +------->E       |
    |                             |
    |  O                          |
    +-----------------------------+
    '''
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
    def lawless_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def ruled_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def base_url(self):
        raise NotImplementedError

    def test_max_page_size(self, app, lawless_preprint_provider, base_url):
        res = app.get(base_url)
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 10

        res = app.get(base_url + '?page[size]=150')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 150

        res = app.get(base_url + '?page[size]=2018')
        assert res.status_code == 200
        assert res.json['links']['meta']['per_page'] == 1000

    def test_no_rules_grabs_all(self, app, lawless_url):
        res = app.get(lawless_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 15

    def test_rules_only_grab_acceptable_subjects(self, app, ruled_url):
        res = app.get(ruled_url)

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 11

    def test_no_rules_with_null_parent_filter(self, app, lawless_url):
        res = app.get(lawless_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 4

    def test_rules_enforced_with_null_parent_filter(self, app, ruled_url):
        res = app.get(ruled_url + 'filter[parents]=null')

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert 'A' in texts
        assert 'H' in texts
        assert 'L' in texts
        assert 'O' not in texts

    def test_no_rules_with_parents_filter(self, app, lawless_url, subB, subI, subM):
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

    def test_rules_enforced_with_parents_filter(self, app, ruled_url, subB, subI, subM):
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

    def test_no_rules_with_parent_filter(self, app, lawless_url, subB, subI, subM):
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

    def test_rules_enforced_with_parent_filter(self, app, ruled_url, subB, subI, subM):
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

    def test_no_rules_with_grandparent_filter(self, app, lawless_url, subA):
        res = app.get(
            lawless_url +
            'filter[parents]={}'.format(
                subA._id))

        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == 3

    def test_rules_enforced_with_grandparent_filter(self, app, ruled_url, subA):
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


@pytest.mark.django_db
class TestPreprintProviderSpecificSubjectsMixin:

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
    def url_1(self):
        raise NotImplementedError

    @pytest.fixture()
    def url_2(self):
        raise NotImplementedError

    def test_mapped_subjects_are_not_shared_list(self, app, url_1, url_2):
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

    def test_mapped_subjects_are_not_shared_filter(self, app, url_1, url_2, root_subject_1, root_subject_2):
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

    def test_mapped_subjects_filter_wrong_provider(self, app, url_1, url_2, root_subject_1, root_subject_2):
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
