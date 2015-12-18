from nose.tools import *  # flake8: noqa
import functools

from framework.auth.core import Auth

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    RegistrationFactory
)

class TestRegistrationEmbeds(ApiTestCase):

    def setUp(self):
        super(TestRegistrationEmbeds, self).setUp()

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

        self.registration = RegistrationFactory(project=self.root_node, is_public=True)
        self.registration_child = RegistrationFactory(project=self.child1, is_public=True)

    def test_embed_children(self):
        url = '/{0}registrations/{1}/?embed=children'.format(API_BASE, self.registration._id)

        res = self.app.get(url, auth=self.user.auth)
        json = res.json
        embeds = json['data']['embeds']
        assert_equal(len(embeds['children']['data']), 2)
        titles = [self.child1.title, self.child2.title]
        for child in embeds['children']['data']:
            assert_in(child['attributes']['title'], titles)

    def test_embed_contributors(self):
        url = '/{0}registrations/{1}/?embed=contributors'.format(API_BASE, self.registration._id)

        res = self.app.get(url, auth=self.user.auth)
        embeds = res.json['data']['embeds']
        ids = [c._id for c in self.contribs] + [self.user._id]
        for contrib in embeds['contributors']['data']:
            assert_in(contrib['id'], ids)

    def test_embed_attributes_not_relationships(self):
        url = '/{}registrations/{}/?embed=title'.format(API_BASE, self.registration._id)

        res = self.app.get(url, auth=self.contrib1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "The following fields are not embeddable: title")


