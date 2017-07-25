from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf.models import Subject
from osf_tests.factories import SubjectFactory, PreprintProviderFactory


class TestPreprintProviderSubjects(ApiTestCase):
    def create_subject_rules(self):
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
        self.subA = SubjectFactory(text='A')
        self.subB = SubjectFactory(text='B', parent=self.subA)
        self.subC = SubjectFactory(text='C', parent=self.subA)
        self.subD = SubjectFactory(text='D', parent=self.subA)
        self.subF = SubjectFactory(text='F', parent=self.subB)
        self.subG = SubjectFactory(text='G', parent=self.subD)
        self.subH = SubjectFactory(text='H')
        self.subI = SubjectFactory(text='I', parent=self.subH)
        self.subJ = SubjectFactory(text='J', parent=self.subI)
        self.subK = SubjectFactory(text='K', parent=self.subI)
        self.subL = SubjectFactory(text='L')
        self.subM = SubjectFactory(text='M', parent=self.subL)
        self.subE = SubjectFactory(text='E', parent=self.subM)
        self.subN = SubjectFactory(text='N', parent=self.subM)
        self.subO = SubjectFactory(text='O')
        rules = [
            ([self.subA._id, self.subB._id], False),
            ([self.subA._id, self.subD._id], True),
            ([self.subH._id, self.subI._id, self.subJ._id], True),
            ([self.subL._id], True)
        ]
        #  This should allow: A, B, D, G, H, I, J, L, M, N and E
        #  This should not allow: C, F, K, O
        return rules

    def setUp(self):
        super(TestPreprintProviderSubjects, self).setUp()
        self.lawless_preprint_provider = PreprintProviderFactory()
        self.ruled_preprint_provider = PreprintProviderFactory()
        self.ruled_preprint_provider.subjects_acceptable = self.create_subject_rules()
        self.ruled_preprint_provider.save()
        self.lawless_url = '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, self.lawless_preprint_provider._id)
        self.ruled_url = '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, self.ruled_preprint_provider._id)

    def test_no_rules_grabs_all(self):
        res = self.app.get(self.lawless_url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 15)

    def test_rules_only_grab_acceptable_subjects(self):
        res = self.app.get(self.ruled_url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 11)

    def test_no_rules_with_null_parent_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parents]=null')

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 4)

    def test_rules_enforced_with_null_parent_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parents]=null')

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 3)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('A', texts)
        assert_in('H', texts)
        assert_in('L', texts)
        assert_not_in('O', texts)

    def test_no_rules_with_parents_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parents]={}'.format(self.subB._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        assert_equal(res.json['data'][0]['attributes']['text'], 'F')

        res = self.app.get(self.lawless_url + 'filter[parents]={}'.format(self.subI._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        res = self.app.get(self.lawless_url + 'filter[parents]={}'.format(self.subM._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

    def test_rules_enforced_with_parents_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parents]={}'.format(self.subB._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 0)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_not_in('F', texts)

        res = self.app.get(self.ruled_url + 'filter[parents]={}'.format(self.subI._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('J', texts)
        assert_not_in('K', texts)

        res = self.app.get(self.ruled_url + 'filter[parents]={}'.format(self.subM._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('N', texts)
        assert_in('E', texts)

    def test_no_rules_with_parent_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parent]={}'.format(self.subB._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        assert_equal(res.json['data'][0]['attributes']['text'], 'F')

        res = self.app.get(self.lawless_url + 'filter[parent]={}'.format(self.subI._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        res = self.app.get(self.lawless_url + 'filter[parent]={}'.format(self.subM._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

    def test_rules_enforced_with_parent_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parent]={}'.format(self.subB._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 0)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_not_in('F', texts)

        res = self.app.get(self.ruled_url + 'filter[parent]={}'.format(self.subI._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('J', texts)
        assert_not_in('K', texts)

        res = self.app.get(self.ruled_url + 'filter[parent]={}'.format(self.subM._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('N', texts)
        assert_in('E', texts)

    def test_no_rules_with_grandparent_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parents]={}'.format(self.subA._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 3)

    def test_rules_enforced_with_grandparent_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parents]={}'.format(self.subA._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('B', texts)
        assert_in('D', texts)
        assert_not_in('C', texts)

class TestPreprintProviderSpecificSubjects(ApiTestCase):
    def setUp(self):
        super(TestPreprintProviderSpecificSubjects, self).setUp()
        self.provider_1 = PreprintProviderFactory()
        self.provider_2 = PreprintProviderFactory()
        self.root_subject_1 = SubjectFactory(text='R1', provider=self.provider_1)
        self.parent_subject_1 = SubjectFactory(text='P1', provider=self.provider_1, parent=self.root_subject_1)
        self.child_subject_1 = SubjectFactory(text='C1', provider=self.provider_1, parent=self.parent_subject_1)
        self.root_subject_2 = SubjectFactory(text='R2', provider=self.provider_2)
        self.parent_subject_2 = SubjectFactory(text='P2', provider=self.provider_2, parent=self.root_subject_2)
        self.child_subject_2 = SubjectFactory(text='C2', provider=self.provider_2, parent=self.parent_subject_2)
        self.url_1 = '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, self.provider_1._id)
        self.url_2 = '/{}preprint_providers/{}/taxonomies/?page[size]=15&'.format(API_BASE, self.provider_2._id)

    def test_mapped_subjects_are_not_shared_list(self):
        res_1 = self.app.get(self.url_1)
        res_2 = self.app.get(self.url_2)

        assert_equal(res_1.status_code, 200)
        assert_equal(res_2.status_code, 200)
        assert_equal(res_1.json['links']['meta']['total'], 3)
        assert_equal(res_2.json['links']['meta']['total'], 3)

        assert_equal(len(set([d['attributes']['text'] for d in res_1.json['data']]) & set([d['attributes']['text'] for d in res_2.json['data']])), 0)
        assert_equal(len(set([d['attributes']['text'] for d in res_1.json['data']]) | set([d['attributes']['text'] for d in res_2.json['data']])), 6)

    def test_mapped_subjects_are_not_shared_filter(self):
        res_1 = self.app.get(self.url_1 + 'filter[parent]={}'.format(self.root_subject_1._id))
        res_2 = self.app.get(self.url_2 + 'filter[parent]={}'.format(self.root_subject_2._id))

        assert_equal(res_1.status_code, 200)
        assert_equal(res_2.status_code, 200)
        assert_equal(res_1.json['links']['meta']['total'], 1)
        assert_equal(res_2.json['links']['meta']['total'], 1)

        assert_equal(len(set([d['attributes']['text'] for d in res_1.json['data']]) & set([d['attributes']['text'] for d in res_2.json['data']])), 0)
        assert_equal(len(set([d['attributes']['text'] for d in res_1.json['data']]) | set([d['attributes']['text'] for d in res_2.json['data']])), 2)

    def test_mapped_subjects_filter_wrong_provider(self):
        res_1 = self.app.get(self.url_1 + 'filter[parent]={}'.format(self.root_subject_2))
        res_2 = self.app.get(self.url_2 + 'filter[parent]={}'.format(self.root_subject_1))

        assert_equal(res_1.status_code, 200)
        assert_equal(res_2.status_code, 200)
        assert_equal(res_1.json['links']['meta']['total'], 0)
        assert_equal(res_2.json['links']['meta']['total'], 0)

class TestPreprintProviderHighlightedSubjects(ApiTestCase):
    def setUp(self):
        super(TestPreprintProviderHighlightedSubjects, self).setUp()
        self.provider = PreprintProviderFactory()
        self.subj_a = SubjectFactory(provider=self.provider, text='A')
        self.subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=self.subj_a, highlighted=True)
        self.url = '/{}preprint_providers/{}/taxonomies/highlighted/'.format(API_BASE, self.provider._id)

    def test_mapped_subjects_filter_wrong_provider(self):
        res = self.app.get(self.url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == self.subj_aa._id

class TestCustomTaxonomy(ApiTestCase):
    def setUp(self):
        super(TestCustomTaxonomy, self).setUp()
        self.osf_provider = PreprintProviderFactory(_id='osf', share_title='bepress')
        self.asdf_provider = PreprintProviderFactory(_id='asdf', share_title='ASDF')
        bepress_subj = SubjectFactory(text='BePress Text', provider=self.osf_provider)
        other_subj = SubjectFactory(text='Other Text', bepress_subject=bepress_subj, provider=self.asdf_provider)
        self.url = '/{}preprint_providers/{}/taxonomies/'

    def test_taxonomy_share_title(self):
        bepress_res = self.app.get(self.url.format(API_BASE, self.osf_provider._id))
        asdf_res = self.app.get(self.url.format(API_BASE, self.asdf_provider._id))

        assert len(bepress_res.json['data']) == len(asdf_res.json['data']) == 1
        assert bepress_res.json['data'][0]['attributes']['share_title'] == self.osf_provider.share_title
        assert asdf_res.json['data'][0]['attributes']['share_title'] == self.asdf_provider.share_title
