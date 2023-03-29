# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pytest
from nose.tools import *  # noqa: F403

from osf_tests import factories
from tests.base import OsfTestCase
from website.util import api_url_for
from website.views import find_bookmark_collection


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchViews(OsfTestCase):

    def setUp(self):
        super(TestSearchViews, self).setUp()
        import website.search.search as search
        search.delete_all()

        robbie = factories.UserFactory(fullname='Robbie Williams')
        self.project = factories.ProjectFactory(creator=robbie)
        self.contrib = factories.UserFactory(fullname='Brian May')
        for i in range(0, 12):
            factories.UserFactory(fullname='Freddie Mercury{}'.format(i))

        self.user_one = factories.AuthUserFactory()
        self.user_two = factories.AuthUserFactory()
        self.project_private_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=False)
        self.project_private_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=False)
        self.project_public_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=True)
        self.project_public_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=True)

    def tearDown(self):
        super(TestSearchViews, self).tearDown()
        import website.search.search as search
        search.delete_all()

    def test_search_views(self):
        #Test search contributor
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': self.contrib.fullname})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        assert_equal(len(result), 1)
        brian = result[0]
        assert_equal(brian['fullname'], self.contrib.fullname)
        assert_in('profile_image_url', brian)
        assert_equal(brian['registered'], self.contrib.is_registered)
        assert_equal(brian['active'], self.contrib.is_active)

        #Test search pagination
        res = self.app.get(url, {'query': 'fr'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(pages, 3)
        assert_equal(page, 0)

        #Test default page 1
        res = self.app.get(url, {'query': 'fr', 'page': 1})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 1)

        #Test default page 2
        res = self.app.get(url, {'query': 'fr', 'page': 2})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 4)
        assert_equal(page, 2)

        #Test smaller pages
        res = self.app.get(url, {'query': 'fr', 'size': 5})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 0)
        assert_equal(pages, 3)

        #Test smaller pages page 2
        res = self.app.get(url, {'query': 'fr', 'page': 2, 'size': 5, })
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 4)
        assert_equal(page, 2)
        assert_equal(pages, 3)

    def test_search_contributor_jobs(self):
        url = api_url_for('search_contributor')

        #Test jobs search
        res = self.app.get(url, {'query': 'Golden Fang LLC'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 1)
        assert_equal(page, 0)

    def test_search_contributor_schools(self):
        url = api_url_for('search_contributor')

        #Test schools search
        res = self.app.get(url, {'query': 'THE University of Narnia'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 1)
        assert_equal(page, 0)

    def test_search(self):

        #Test search projects
        url = '/search/'
        res = self.app.get(url, {'q': self.project.title})
        assert_equal(res.status_code, 200)
