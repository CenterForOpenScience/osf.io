from nose.tools import *

from framework.auth.core import Auth

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestNodeRelationshipInstitution(ApiTestCase):
    def setUp(self):
        super(TestNodeRelationshipInstitution, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.node = NodeFactory(is_public=True)
        self.node_institution_url = '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, self.node._id)

    def test_node_with_no_permissions(self):
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        res = self.app.put_json_api(
            self.node_institution_url,
            {'data': {'type': 'institutions', 'id': self.institution._id}},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)

    def test_user_with_no_institution(self):
        node = NodeFactory(creator=self.user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'type': 'institutions', 'id': self.institution._id}},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)

    def test_institution_doesnt_exist(self):
        node = NodeFactory(creator=self.user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'type': 'institutions', 'id': 'not_an_id'}},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 404)

    def test_wrong_type(self):
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        node = NodeFactory(creator=self.user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'type': 'not_institution', 'id': self.institution._id}},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 409)

    def test_user_with_institution_and_permissions(self):
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        node = NodeFactory(creator=self.user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'type': 'institutions', 'id': self.institution._id}},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(data['type'], 'institutions')
        assert_equal(data['id'], self.institution._id)
        node.reload()
        assert_equal(node.primary_institution, self.institution)

    def test_user_with_institution_and_permissions_through_patch(self):
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        node = NodeFactory(creator=self.user)
        res = self.app.patch_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'type': 'institutions', 'id': self.institution._id}},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(data['type'], 'institutions')
        assert_equal(data['id'], self.institution._id)
        node.reload()
        assert_equal(node.primary_institution, self.institution)

    def test_user_with_institution_and_permissions_wrong_format(self):
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        node = NodeFactory(creator=self.user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': {'id': self.institution._id}},
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)

    def test_remove_institution_with_no_permissions(self):
        res = self.app.put_json_api(
            self.node_institution_url,
            {'data': None},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)

    def test_remove_institution_with_affiliated_user(self):
        node = NodeFactory(creator=self.user)
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        node.primary_institution = self.institution
        node.save()

        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': None},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        node.reload()
        assert_equal(node.primary_institution, None)

    def test_remove_institution_not_admin(self):
        node = NodeFactory(creator=self.user)
        user = AuthUserFactory()
        node.primary_institution = self.institution
        node.add_contributor(user, auth=Auth(self.user))
        node.save()

        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': None},
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(node.primary_institution, self.institution)

    def test_remove_instituion_not_admin_but_affiliated(self):
        node = NodeFactory(creator=self.user)
        user = AuthUserFactory()
        user.affiliated_institutions.append(self.institution)
        user.save()
        node.primary_institution = self.institution
        node.add_contributor(user, auth=Auth(self.user))
        node.save()

        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': None},
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(node.primary_institution, self.institution)

    def test_remove_institution_admin(self):
        node = NodeFactory(creator=self.user)
        node.primary_institution = self.institution
        node.save()

        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            {'data': None},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        node.reload()
        assert_equal(node.primary_institution, None)

    def test_retrieve_public_node_no_inst(self):
        res = self.app.get(self.node_institution_url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'], None)
        assert_in(self.node_institution_url, res.json['links']['self'])

    def test_retrieve_public_node_with_inst(self):
        self.node.primary_institution = self.institution
        self.node.save()

        res = self.app.get(self.node_institution_url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['type'], 'institutions')
        assert_equal(res.json['data']['id'], self.institution._id)

    def test_retrieve_private_node_no_auth(self):
        self.node.is_public = False
        self.node.save()

        res = self.app.get(self.node_institution_url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_retrieve_private_node_with_auth_no_inst(self):
        node = NodeFactory(is_public=False, creator=self.user)

        res = self.app.get(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'], None)

    def test_retrieve_private_node_with_auth_with_inst(self):
        node = NodeFactory(is_public=False, creator=self.user)
        node.primary_institution = self.institution
        node.save()

        res = self.app.get(
            '/{0}nodes/{1}/relationships/institution/'.format(API_BASE, node._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['type'], 'institutions')
        assert_equal(res.json['data']['id'], self.institution._id)

    def test_retrieve_private_node_wrong_auth(self):
        self.node.is_public = False
        self.node.save()

        res = self.app.get(self.node_institution_url, expect_errors=True, auth=self.user.auth)

        assert_equal(res.status_code, 403)
