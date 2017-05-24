import pytest
import functools

from framework.auth.core import Auth
from tests.json_api_test_app import JSONAPITestApp
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

@pytest.mark.django_db
class TestNodeEmbeds:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
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

    def test_node_embeds(self):

    #   test_embed_children
        url = '/{0}nodes/{1}/?embed=children'.format(API_BASE, self.root_node._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        ids = [self.child1._id, self.child2._id]
        for child in embeds['children']['data']:
            assert child['id'] in ids

    #   test_embed_parent
        url = '/{0}nodes/{1}/?embed=parent'.format(API_BASE, self.child1._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        assert embeds['parent']['data']['id'] == self.root_node._id

    #   test_embed_no_parent
        url = '/{0}nodes/{1}/?embed=parent'.format(API_BASE, self.root_node._id)

        res = self.app.get(url, auth=self.user.auth)
        data = res.json['data']
        assert 'embeds' not in data

    #   test_embed_contributors
        url = '/{0}nodes/{1}/?embed=contributors'.format(API_BASE, self.child1._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        ids = [c._id for c in self.contribs] + [self.user._id]
        ids = ['{}-{}'.format(self.child1._id, id_) for id_ in ids]
        for contrib in embeds['contributors']['data']:
            assert contrib['id'] in ids

    #   test_embed_children_filters_unauthorized
        url = '/{0}nodes/{1}/?embed=children'.format(API_BASE, self.root_node._id)

        res = self.app.get(url, auth=self.contrib1.auth)
        embeds = res.json['data']['embeds']
        ids = [c['id'] for c in embeds['children']['data']]
        assert self.child2._id not in ids
        assert self.child1._id in ids

    #   test_embed_parent_unauthorized
        url = '/{0}nodes/{1}/?embed=parent'.format(API_BASE, self.subchild._id)

        res = self.app.get(url, auth=self.contrib1.auth)
        assert 'errors' in res.json['data']['embeds']['parent']
        assert res.json['data']['embeds']['parent']['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    #   test_embed_attributes_not_relationships
        url = '/{}nodes/{}/?embed=title'.format(API_BASE, self.root_node._id)

        res = self.app.get(url, auth=self.contrib1.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The following fields are not embeddable: title'

    #   test_embed_contributors_pagination
        url = '/{}nodes/{}/?embed=contributors'.format(API_BASE, self.root_node._id)
        res = self.app.get(url, auth=self.contrib1.auth)
        assert res.status_code == 200
        assert res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic'] == 3

    #   test_embed_contributors_updated_pagination
        url = '/{}nodes/{}/?version=2.1&embed=contributors'.format(API_BASE, self.root_node._id)
        res = self.app.get(url, auth=self.contrib1.auth)
        assert res.status_code == 200
        assert res.json['data']['embeds']['contributors']['meta']['total_bibliographic'] == 3
