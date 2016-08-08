from nose.tools import *  # flake8: noqa
import functools

from modularodm import Q
from tests.base import ApiTestCase
from website.project.taxonomies import Subject
from api.base.settings.defaults import API_BASE


class TestPlosTaxonomy(ApiTestCase):
    def setUp(self):
        super(TestPlosTaxonomy, self).setUp()
        self.subjects = Subject.find(
            Q('type', 'eq', 'plos')
        )
        self.url = '/{}taxonomies/plos/'.format(API_BASE)
        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def test_plos_taxonomy_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_plos_taxonomy_top_level(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break  # Can only test what is returned in first page
            assert_equal(self.data[index]['type'], 'taxonomies')
            assert_equal(self.data[index]['id'], subject._id)

    def test_plos_taxonomy_text(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break
            assert_equal(self.data[index]['attributes']['text'], subject.text)

    def test_plos_taxonomy_parent_ids(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break
            assert_equal(self.data[index]['attributes']['parent_ids'], subject.parent_ids)

    def test_plos_taxonomy_type(self):
        for index, subject in enumerate(self.subjects):
            if index >= len(self.data): break
            assert_equal(self.data[index]['attributes']['type'], subject.type)

    def test_plos_taxonomy_filter_top_level(self):
        top_level_url = self.url + '?filter[parent_ids]=null&page[size]=11'

        res = self.app.get(top_level_url)
        assert_equal(res.status_code, 200)

        data = res.json['data']
        for subject in data:
            assert_equal(len(subject['attributes']['parent_ids']), 1)
            assert_equal(subject['attributes']['parent_ids'][0], None)

    # def test_plos_taxonomy_filter_by_parent(self):
    #     top_level_subject = Subject.find(Q('parent_ids', 'eq', None))[0]
    #
    #     children_url = self.url + '?filter[parent_ids]={}'.format(top_level_subject._id)
    #
    #     res = self.app.get(children_url)
    #     assert_equal(res.status_code, 200)
    #
    #     data = res.json['data']
    #     for subject in data:
    #         assert_in(top_level_subject._id, subject['attributes']['parent_ids'])
