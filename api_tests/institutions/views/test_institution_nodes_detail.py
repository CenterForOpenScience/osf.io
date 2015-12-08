from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionNodeDetail(ApiTestCase):
    def setUp(self):
        super(TestInstitutionNodeDetail, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.private_node = NodeFactory(creator=self.user, is_public=False)
        self.public_node = NodeFactory(is_public=True)
        self.private_node.primary_institution = self.institution
        self.public_node.primary_institution = self.institution
        self.private_node.save()
        self.public_node.save()
        self.institution_node_url = '/{0}institutions/{1}/nodes/'.format(API_BASE, self.institution._id)
        self.other_node = NodeFactory(is_public=True)

    def test_return_wrong_id(self):
        url = self.institution_node_url + self.other_node._id + '/'
        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, 404)

    def test_return_private_node(self):
        url = self.institution_node_url + self.private_node._id + '/'
        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_return_public_node(self):
        url = self.institution_node_url + self.public_node._id + '/'
        res = self.app.get(url)

        assert_equal(res.status_code, 200)
        assert_equal(self.public_node.title, res.json['data']['attributes']['title'])
        assert_equal(self.public_node._id, res.json['data']['id'])

    def test_return_private_node_with_auth(self):
        url = self.institution_node_url + self.private_node._id + '/'
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(self.private_node.title, res.json['data']['attributes']['title'])
        assert_equal(self.private_node._id, res.json['data']['id'])
