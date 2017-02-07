# -*- coding: utf-8 -*-
from nose import tools as nt

from framework.auth.core import Auth

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils

from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


class TestFileFiltering(ApiTestCase):
    def setUp(self):
        super(TestFileFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.file1 = api_utils.create_test_file(
            self.node, self.user, filename='file1')
        self.file2 = api_utils.create_test_file(
            self.node, self.user, filename='file2')
        self.file3 = api_utils.create_test_file(
            self.node, self.user, filename='file3')
        self.file4 = api_utils.create_test_file(
            self.node, self.user, filename='file4')

    def test_get_all_files(self):
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/'.format(API_BASE, self.node._id),
            auth=self.user.auth
        )
        data = res.json.get('data')
        nt.assert_equal(len(data), 4)

    def test_filter_on_tag(self):
        self.file1.add_tag('new', Auth(self.user))
        self.file2.add_tag('new', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        data = res.json.get('data')
        nt.assert_equal(len(data), 2)
        names = [f['attributes']['name'] for f in data]
        nt.assert_in('file1', names)
        nt.assert_in('file2', names)

    def test_filtering_tags_exact(self):
        self.file1.add_tag('cats', Auth(self.user))
        self.file2.add_tag('cats', Auth(self.user))
        self.file1.add_tag('cat', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_filtering_tags_capitalized_query(self):
        self.file1.add_tag('cat', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=CAT'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_filtering_tags_capitalized_tag(self):
        self.file1.add_tag('CAT', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_filtering_on_multiple_tags(self):
        self.file1.add_tag('cat', Auth(self.user))
        self.file1.add_tag('sand', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)

    def test_filtering_on_multiple_tags_must_match_both(self):
        self.file1.add_tag('cat', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 0)

    def test_filtering_by_tags_returns_distinct(self):
        # regression test for returning multiple of the same file
        self.file1.add_tag('cat', Auth(self.user))
        self.file1.add_tag('cAt', Auth(self.user))
        self.file1.add_tag('caT', Auth(self.user))
        self.file1.add_tag('CAT', Auth(self.user))
        res = self.app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, self.node._id
            ),
            auth=self.user.auth
        )
        nt.assert_equal(len(res.json.get('data')), 1)
