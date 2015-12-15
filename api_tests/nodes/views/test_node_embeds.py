from nose.tools import *  # flake8: noqa
import functools

from framework.auth.core import Auth

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

class TestNodeEmbeds(ApiTestCase):

    def setUp(self):
        super(TestNodeEmbeds, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        make_public_node = functools.partial(ProjectFactory, is_public=False, creator=self.user)
        self.root_node = make_public_node()
        self.child1 = make_public_node(parent=self.root_node)
        self.child2 = make_public_node(parent=self.root_node)

        self.contribs = [AuthUserFactory() for i in range(2)]
        for contrib in self.contribs:
            self.root_node.add_contributor(contrib, ['read', 'write'], auth=self.auth, save=True)
            self.child1.add_contributor(contrib, ['read', 'write'], auth=self.auth, save=True)

        self.contrib1 = self.contribs[0]
        self.contrib2 = self.contribs[1]
        self.subchild = ProjectFactory(parent=self.child2, creator=self.contrib1)

    def test_embed_children(self):
        url = '/{0}nodes/{1}/?embed=children'.format(API_BASE, self.root_node._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        ids = [self.child1._id, self.child2._id]
        for child in embeds['children']['data']:
            assert_in(child['id'], ids)

    def test_embed_parent(self):
        url = '/{0}nodes/{1}/?embed=parent'.format(API_BASE, self.child1._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        assert_equal(embeds['parent']['data']['id'], self.root_node._id)

    def test_embed_contributors(self):
        url = '/{0}nodes/{1}/?embed=contributors'.format(API_BASE, self.child1._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        ids = [c._id for c in self.contribs] + [self.user._id]
        for contrib in embeds['contributors']['data']:
            assert_in(contrib['id'], ids)

    def test_embed_children_filters_unauthorized(self):
        url = '/{0}nodes/{1}/?embed=children'.format(API_BASE, self.root_node)

        res = self.app.get(url, auth=self.contrib1.auth)
        embeds = res.json['data']['embeds']
        ids = [c['id'] for c in embeds['children']['data']]
        assert_not_in(self.child2._id, ids)
        assert_in(self.child1._id, ids)

    def test_embed_parent_unauthorized(self):
        url = '/{0}nodes/{1}/?embed=parent'.format(API_BASE, self.subchild)

        res = self.app.get(url, auth=self.contrib1.auth)
        assert_in('errors', res.json['data']['embeds']['parent'])
        assert_equal(res.json['data']['embeds']['parent']['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_embed_attributes_not_relationships(self):
        url = '/{}nodes/{}/?embed=title'.format(API_BASE, self.root_node)

        res = self.app.get(url, auth=self.contrib1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "The following fields are not embeddable: title")

