from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import SubjectFactory, PreprintProviderFactory


class TestPreprintProviderSubjects(ApiTestCase):
    def create_subject_rules(self):
        '''
        Subject Hierarchy
        +-----------------------------+
        |                    +-->E    |
        |      +-------->B+--+        |
        |      |             +-->F    |
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
        self.subB = SubjectFactory(text='B', parents=[self.subA])
        self.subC = SubjectFactory(text='C', parents=[self.subA])
        self.subD = SubjectFactory(text='D', parents=[self.subA])
        self.subF = SubjectFactory(text='F', parents=[self.subB])
        self.subG = SubjectFactory(text='G', parents=[self.subD])
        self.subH = SubjectFactory(text='H')
        self.subI = SubjectFactory(text='I', parents=[self.subH])
        self.subJ = SubjectFactory(text='J', parents=[self.subI])
        self.subK = SubjectFactory(text='K', parents=[self.subI])
        self.subL = SubjectFactory(text='L')
        self.subM = SubjectFactory(text='M', parents=[self.subL])
        self.subE = SubjectFactory(text='E', parents=[self.subB, self.subM])
        self.subN = SubjectFactory(text='N', parents=[self.subM])
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

    def test_no_rules_with_parent_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parents]=' + self.subB._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        res = self.app.get(self.lawless_url + 'filter[parents]=' + self.subI._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        res = self.app.get(self.lawless_url + 'filter[parents]=' + self.subM._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

    def test_rules_enforced_with_parent_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parents]=' + self.subB._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('E', texts)
        assert_not_in('F', texts)

        res = self.app.get(self.ruled_url + 'filter[parents]=' + self.subI._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 1)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('J', texts)
        assert_not_in('K', texts)

        res = self.app.get(self.ruled_url + 'filter[parents]=' + self.subM._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('N', texts)
        assert_in('E', texts)

    def test_no_rules_with_grandparent_filter(self):
        res = self.app.get(self.lawless_url + 'filter[parents]=' + self.subA._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 3)

    def test_rules_enforced_with_grandparent_filter(self):
        res = self.app.get(self.ruled_url + 'filter[parents]=' + self.subA._id)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)
        texts = [item['attributes']['text'] for item in res.json['data']]
        assert_in('B', texts)
        assert_in('D', texts)
        assert_not_in('C', texts)

