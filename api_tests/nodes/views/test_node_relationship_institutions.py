from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from osf_tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

from website.util import permissions


class TestNodeRelationshipInstitutions(ApiTestCase):

    def setUp(self):
        super(TestNodeRelationshipInstitutions, self).setUp()

        self.institution2 = InstitutionFactory()
        self.institution1 = InstitutionFactory()

        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.user.affiliated_institutions.add(self.institution2)
        self.user.save()

        self.read_write_contributor = AuthUserFactory()
        self.read_write_contributor_institution = InstitutionFactory()
        self.read_write_contributor.affiliated_institutions.add(self.read_write_contributor_institution)
        self.read_write_contributor.save()

        self.read_only_contributor = AuthUserFactory()
        self.read_only_contributor_institution = InstitutionFactory()
        self.read_only_contributor.affiliated_institutions.add(self.read_only_contributor_institution)
        self.read_only_contributor.save()

        self.node = NodeFactory(creator=self.user)
        self.node.add_contributor(self.read_write_contributor, permissions=[permissions.WRITE])
        self.node.add_contributor(self.read_only_contributor, permissions=[permissions.READ])
        self.node.save()

        self.node_institutions_url = '/{0}nodes/{1}/relationships/institutions/'.format(API_BASE, self.node._id)

    def create_payload(self, *institution_ids):
        data = []
        for id_ in institution_ids:
            data.append({'type': 'institutions', 'id': id_})
        return {'data': data}

    def test_node_with_no_permissions(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution1)
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

    def test_institution_does_not_exist(self):
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
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

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
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_in(self.institution2, self.node.affiliated_institutions.all())

    def test_user_with_institution_and_permissions_through_patch(self):
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

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
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_in(self.institution2, self.node.affiliated_institutions.all())

    def test_remove_institutions_with_no_permissions(self):
        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload(),
            expect_errors=True
        )
        assert_equal(res.status_code, 401)

    def test_remove_institutions_with_affiliated_user(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())

        res = self.app.put_json_api(
            self.node_institutions_url,
            {'data': []},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_equal(self.node.affiliated_institutions.count(), 0)

    def test_using_post_making_no_changes_returns_204(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions.all())

    def test_put_not_admin_but_affiliated(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution1)
        user.save()
        self.node.add_contributor(user)
        self.node.save()

        res = self.app.put_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=user.auth
        )

        self.node.reload()
        assert_equal(res.status_code, 200)
        assert_in(self.institution1, self.node.affiliated_institutions.all())

    def test_retrieve_private_node_no_auth(self):
        res = self.app.get(self.node_institutions_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_add_through_patch_one_inst_to_node_with_inst(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

        res = self.app.patch_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_in(self.institution2, self.node.affiliated_institutions.all())

    def test_add_through_patch_one_inst_while_removing_other(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

        res = self.app.patch_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())
        assert_in(self.institution2, self.node.affiliated_institutions.all())

    def test_add_one_inst_with_post_to_node_with_inst(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

        res = self.app.post_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution2._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        self.node.reload()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_in(self.institution2, self.node.affiliated_institutions.all())

    def test_delete_nothing(self):
        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 204)

    def test_delete_existing_inst(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())

    def test_delete_not_affiliated_and_affiliated_insts(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        assert_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id, self.institution2._id),
            auth=self.user.auth,
        )

        assert_equal(res.status_code, 204)
        self.node.reload()
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())
        assert_not_in(self.institution2, self.node.affiliated_institutions.all())

    def test_delete_user_is_admin(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

    def test_delete_user_is_read_write(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution1)
        user.save()
        self.node.add_contributor(user)
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()

        res = self.app.delete_json_api(
            self.node_institutions_url,
            self.create_payload(self.institution1._id),
            auth=user.auth
        )

        assert_equal(res.status_code, 204)

    def test_delete_user_is_read_only(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution1)
        user.save()
        self.node.add_contributor(user, permissions=[permissions.READ])
        self.node.affiliated_institutions.add(self.institution1)
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
        node.affiliated_institutions.add(self.institution1)
        node.save()
        assert_in(self.institution1, node.affiliated_institutions.all())

        res = self.app.delete_json_api(
            '/{0}nodes/{1}/relationships/institutions/'.format(API_BASE, node._id),
            self.create_payload(self.institution1._id),
            auth=user.auth,
        )

        assert_equal(res.status_code, 204)
        node.reload()
        assert_not_in(self.institution1, node.affiliated_institutions.all())

    def test_admin_can_add_affiliated_institution(self):
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.institution1._id
            }]
        }
        res = self.app.post_json_api(self.node_institutions_url, payload, auth=self.user.auth)
        self.node.reload()
        assert_equal(res.status_code, 201)
        assert_in(self.institution1, self.node.affiliated_institutions.all())

    def test_admin_can_remove_admin_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.institution1)
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.institution1._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.user.auth)
        self.node.reload()
        assert_equal(res.status_code, 204)
        assert_not_in(self.institution1, self.node.affiliated_institutions.all())

    def test_admin_can_remove_read_write_contributor_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.read_write_contributor_institution)
        self.node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.read_write_contributor_institution._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.user.auth)
        self.node.reload()
        assert_equal(res.status_code, 204)
        assert_not_in(self.read_write_contributor_institution, self.node.affiliated_institutions.all())

    def test_read_write_contributor_can_add_affiliated_institution(self):
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.read_write_contributor_institution._id
            }]
        }
        res = self.app.post_json_api(self.node_institutions_url, payload, auth=self.read_write_contributor.auth)
        self.node.reload()
        assert_equal(res.status_code, 201)
        assert_in(self.read_write_contributor_institution, self.node.affiliated_institutions.all())

    def test_read_write_contributor_can_remove_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.read_write_contributor_institution)
        self.node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.read_write_contributor_institution._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.read_write_contributor.auth)
        self.node.reload()
        assert_equal(res.status_code, 204)
        assert_not_in(self.read_write_contributor_institution, self.node.affiliated_institutions.all())

    def test_read_write_contributor_cannot_remove_admin_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.institution1._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.read_write_contributor.auth, expect_errors=True)
        self.node.reload()
        assert_equal(res.status_code, 403)
        assert_in(self.institution1, self.node.affiliated_institutions.all())

    def test_read_only_contributor_cannot_remove_admin_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.institution1)
        self.node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.institution1._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.read_only_contributor.auth, expect_errors=True)
        self.node.reload()
        assert_equal(res.status_code, 403)
        assert_in(self.institution1, self.node.affiliated_institutions.all())

    def test_read_only_contributor_cannot_add_affiliated_institution(self):
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.read_only_contributor_institution._id
            }]
        }
        res = self.app.post_json_api(self.node_institutions_url, payload, auth=self.read_only_contributor.auth, expect_errors=True)
        self.node.reload()
        assert_equal(res.status_code, 403)
        assert_not_in(self.read_write_contributor_institution, self.node.affiliated_institutions.all())

    def test_read_only_contributor_cannot_remove_affiliated_institution(self):
        self.node.affiliated_institutions.add(self.read_only_contributor_institution)
        self.node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': self.read_only_contributor_institution._id
            }]
        }
        res = self.app.delete_json_api(self.node_institutions_url, payload, auth=self.read_only_contributor.auth, expect_errors=True)
        self.node.reload()
        assert_equal(res.status_code, 403)
        assert_in(self.read_only_contributor_institution, self.node.affiliated_institutions.all())
