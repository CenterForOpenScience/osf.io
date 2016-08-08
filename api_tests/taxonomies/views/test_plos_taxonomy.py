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
