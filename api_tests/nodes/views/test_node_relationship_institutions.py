from nose.tools import *

from framework.auth import Auth

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestNodeRelationshipInstitutions(ApiTestCase):
    def setUp(self):
        super(TestNodeRelationshipInstitutions, self).setUp()
        self.user = AuthUserFactory()
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.append(self.institution1)
        self.user.affiliated_institutions.append(self.institution2)
        self.user.save()
        self.node = NodeFactory(creator=self.user)
        self.node_institutions_url = '/{0}nodes/{1}/relationships/institutions/'.format(API_BASE, self.node._id)

    def create_payload(self, *institution_ids):
        data = []
        for id_ in institution_ids:
            data.append({'type': 'institutions', 'id': id_})
        return {'data': data}

    def test_node_with_no_permissions(self):
        user = AuthUserFactory()
        user.affiliated_institutions.append(self.institution1)
        user.save()
        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload([self.institution1._id]),
            auth=user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, 403)

    def test_user_with_no_institution(self):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        res = self.app.put_json_api(
            '/{0}nodes/{1}/relationships/institutions/'.format(API_BASE, node._id),
            self.create_payload(self.institution1._id),
            expect_errors=True,
            auth=user.auth
        )

        assert_equal(res.status_code, 403)

    def test_get_public_node(self):
        self.node.is_public = True
        self.node.save()

        res = self.app.get(
            self.node_institutions_url
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'], [])

    def test_institution_doesnt_exist(self):
        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload('not_an_id'),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 404)

    def test_wrong_type(self):
        res = self.app.put_json_api(
            self.node_institutions_url,
            {'data': [{'type': 'not_institution', 'id': self.institution1._id}]},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 409)

    def test_user_with_institution_and_permissions(self):
        assert_not_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert_in(self.institution1._id, ret_institutions)
        assert_in(self.institution2._id, ret_institutions)

        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_user_with_institution_and_permissions_through_patch(self):
        assert_not_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert_in(self.institution1._id, ret_institutions)
        assert_in(self.institution2._id, ret_institutions)

        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_user_with_institution_and_permissions_through_patch(self):
        assert_not_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert_in(self.institution1._id, ret_institutions)
        assert_in(self.institution2._id, ret_institutions)

        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_remove_institutions_with_no_permissions(self):
        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload(),
            expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_remove_institutions_with_affiliated_user(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)

        res = self.app.put_json_api(
            self.node_institutions_url,
            {'data': []},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_equal(self.node.affiliated_institutions, [])

    def test_using_post_making_no_changes_returns_204(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)

    def test_put_not_admin_but_affiliated(self):
        user = AuthUserFactory()
        user.affiliated_institutions.append(self.institution1)
        user.save()
        self.node.add_contributor(user, auth=Auth(self.user))
        self.node.save()

        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        assert_equal(self.node.affiliated_institutions, [])

    def test_retrieve_private_node_no_auth(self):
        res = self.app.get(self.node_institutions_url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_add_through_patch_one_inst_to_node_with_inst(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.patch_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_add_through_patch_one_inst_while_removing_other(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.patch_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_add_one_inst_with_post_to_node_with_inst(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_in(self.institution2, self.node.affiliated_institutions)

    def test_delete_nothing(self):
        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

    def test_delete_existing_inst(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions)

    def test_delete_not_affiliated_and_affiliated_insts(self):
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth,
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions)
        assert_not_in(self.institution2, self.node.affiliated_institutions)

    def test_delete_user_is_not_admin(self):
        user = AuthUserFactory()
        user.affiliated_institutions.append(self.institution1)
        user.save()
        self.node.affiliated_institutions.append(self.institution1)
        self.node.save()

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        node.affiliated_institutions.append(self.institution1)
        node.save()
        assert_in(self.institution1, node.affiliated_institutions)

        res = self.app.delete_json_api(
            '/{0}nodes/{1}/relationships/institutions/'.format(API_BASE, node._id),
            self.create_payload(self.institution1._id),
            auth=user.auth,
        )

        assert_equal(res.status_code, 204)
        node.reload()
        assert_not_in(self.institution1, node.affiliated_institutions)
