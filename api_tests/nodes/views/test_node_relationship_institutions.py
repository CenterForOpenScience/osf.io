from nose.tools import *

from framework.auth.core import Auth

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestNodeRelationshipInstitution(ApiTestCase):
    def setUp(self):
        super(TestNodeRelationshipInstitution, self).setUp()
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


