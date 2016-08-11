from nose.tools import *  # flake8: noqa

from modularodm import Q
from tests.base import ApiTestCase
from tests.factories import SubjectFactory
from website.project.taxonomies import Subject
from api.base.settings.defaults import API_BASE


class TestTaxonomy(ApiTestCase):
    def setUp(self):
        super(TestTaxonomy, self).setUp()

        # Subject 1 has 3 children
        self.subject1 = SubjectFactory()
        self.subject1_child1 = SubjectFactory(parent_ids=[self.subject1._id])
        self.subject1_child2 = SubjectFactory(parent_ids=[self.subject1._id])

        # Subject 2 has a child whose parent is both subject 1 and subject 2
        self.subject2 = SubjectFactory()
        self.subject2_child1_subject1_child3 = SubjectFactory(parent_ids=[self.subject1._id, self.subject2._id])

        self.subjects = Subject.find(
            Q('type', 'eq', 'test')
        )
        self.url = '/{}taxonomies/'.format(API_BASE)
        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def tearDown(self):
        super(TestTaxonomy, self).tearDown()
        Subject.remove()

    def test_taxonomy_success(self):
        assert_greater(len(self.subjects), 0)  # make sure there are subjects to filter through
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_taxonomy_text(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break  # only iterate though first page of results
            assert_equal(self.data[index]['attributes']['text'], subject.text)

    def test_taxonomy_parent_ids(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break
            assert_equal(self.data[index]['attributes']['parent_ids'], subject.parent_ids)

    def test_taxonomy_type(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break
            assert_equal(self.data[index]['attributes']['type'], subject.type)

    def test_taxonomy_filter_top_level(self):
        top_level_subjects = Subject.find(
            Q('parent_ids', 'eq', [])
        )
        top_level_url = self.url + '?filter[parent_ids]=null&page[size]=11'

        res = self.app.get(top_level_url)
        assert_equal(res.status_code, 200)

        data = res.json['data']
        assert_equal(len(top_level_subjects), len(data))
        for subject in data:
            assert_equal(subject['attributes']['parent_ids'], [])

    def test_taxonomy_filter_by_parent(self):
        children_subjects = Subject.find(
            Q('parent_ids', 'ne', [])
        )
        children_url = self.url + '?filter[parent_ids]={}'.format(self.subject1._id)

        res = self.app.get(children_url)
        assert_equal(res.status_code, 200)

        data = res.json['data']
        assert_equal(len(children_subjects), len(data))
        for subject in data:
            assert_in(self.subject1._id, subject['attributes']['parent_ids'])
