# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory, InstitutionFactory

from api.base.settings.defaults import API_BASE

class TestUserInstititutionRelationship(ApiTestCase):

    def setUp(self):
        super(TestUserInstititutionRelationship, self).setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.url = '/{}users/{}/relationships/institutions/'.format(API_BASE, self.user._id)
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.append(self.institution1)
        self.user.affiliated_institutions.append(self.institution2)
        self.user.save()

    def test_get_relationship_institutions(self):
        res = self.app.get(
            self.url, auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        assert_in(self.user.absolute_api_v2_url + 'relationships/institutions/', res.json['links']['self'])
        assert_in(self.user.absolute_api_v2_url + 'institutions/', res.json['links']['html'])

        ids = [val['id'] for val in res.json['data']]
        assert_in(self.institution1._id, ids)
        assert_in(self.institution2._id, ids)

    def test_get_institutions_relationship_while_logged_out(self):
        res = self.app.get(
            self.url
        )
        ids = [val['id'] for val in res.json['data']]
        assert_in(self.institution1._id, ids)
        assert_in(self.institution2._id, ids)

    def test_post_with_auth(self):
        res = self.app.post_json_api(
            self.url, {},
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 405)

    def test_put_with_auth(self):
        res = self.app.put_json_api(
            self.url, {},
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 405)

    def test_post_without_auth(self):
        res = self.app.post_json_api(
            self.url, {}, expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_put_without_auth(self):
        res = self.app.put_json_api(
            self.url, {}, expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_delete_no_auth(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions', 'id': self.institution1._id}
            ]},
            expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_delete_wrong_auth(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions', 'id': self.institution1._id}
            ]},
            auth=self.user2.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_delete_one(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions', 'id': self.institution1._id}
            ]},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

        self.user.reload()

        ids = [inst._id for inst in self.user.affiliated_institutions]
        assert_not_in(self.institution1._id, ids)
        assert_in(self.institution2._id, ids)

    def test_type_mistyped(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'wow', 'id': self.institution1._id}
            ]},
            auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 409)

    def test_delete_multiple(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions', 'id': self.institution1._id},
                {'type': 'institutions', 'id': self.institution2._id}
            ]},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

        self.user.reload()

        ids = [inst._id for inst in self.user.affiliated_institutions]
        assert_not_in(self.institution1._id, ids)
        assert_not_in(self.institution2._id, ids)

    def test_delete_one_not_existing(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions', 'id': 'not_an_id'}
            ]},
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

        self.user.reload()

        ids = [inst._id for inst in self.user.affiliated_institutions]
        assert_in(self.institution1._id, ids)
        assert_in(self.institution2._id, ids)

    def test_attempt_payload_not_in_array(self):
        res = self.app.delete_json_api(
            self.url,
            {'data':
                {'type': 'institutions', 'id': self.institution1._id}
            },
            auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 400)

    def test_attempt_with_no_type_field(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'id': self.institution1._id}
            ]},
            auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 400)

    def test_attempt_with_no_id_field(self):
        res = self.app.delete_json_api(
            self.url,
            {'data': [
                {'type': 'institutions'}
            ]},
            auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 400)
