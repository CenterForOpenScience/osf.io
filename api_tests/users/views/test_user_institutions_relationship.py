# -*- coding: utf-8 -*-
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)


@pytest.mark.django_db
class TestUserInstititutionRelationship:

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_two(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self, institution_one, institution_two):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution_one)
        user.affiliated_institutions.add(institution_two)
        user.save()
        return user

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url(self, user):
        return '/{}users/{}/relationships/institutions/'.format(API_BASE, user._id)

    # def setUp(self):
    #     super(TestUserInstititutionRelationship, self).setUp()
    #     self.user = AuthUserFactory()
    #     self.user2 = AuthUserFactory()
    #     self.url = '/{}users/{}/relationships/institutions/'.format(API_BASE, self.user._id)
    #     self.institution_one = InstitutionFactory()
    #     self.institution_two = InstitutionFactory()
    #     self.user.affiliated_institutions.add(self.institution_one)
    #     self.user.affiliated_institutions.add(self.institution_two)
    #     self.user.save()

    def test_get(self, app, user, institution_one, institution_two, url):

    # def test_get_relationship_institutions(self):
        res = app.get(
            url, auth=user.auth
        )

        assert res.status_code == 200

        assert user.absolute_api_v2_url + 'relationships/institutions/' in res.json['links']['self']
        assert user.absolute_api_v2_url + 'institutions/' in res.json['links']['html']

        ids = [val['id'] for val in res.json['data']]
        assert institution_one._id in ids
        assert institution_two._id in ids

    # def test_get_institutions_relationship_while_logged_out(self):
        res = app.get(
            url
        )
        ids = [val['id'] for val in res.json['data']]
        assert institution_one._id in ids
        assert institution_two._id in ids

    def test_delete_one(self, app, user, institution_one, institution_two, url):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id}
            ]},
            auth=user.auth
        )

        assert res.status_code == 204

        user.reload()

        ids = list(user.affiliated_institutions.values_list('_id', flat=True))
        assert institution_one._id not in ids
        assert institution_two._id in ids

    def test_delete_multiple(self, app, user, institution_one, institution_two, url):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id},
                {'type': 'institutions', 'id': institution_two._id}
            ]},
            auth=user.auth
        )

        assert res.status_code == 204

        user.reload()

        ids = list(user.affiliated_institutions.values_list('_id', flat=True))
        assert institution_one._id not in ids
        assert institution_two._id not in ids

    def test_delete_one_not_existing(self, app, user, institution_one, institution_two, url):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': 'not_an_id'}
            ]},
            auth=user.auth
        )

        assert res.status_code == 204

        user.reload()

        ids = list(user.affiliated_institutions.values_list('_id', flat=True))
        assert institution_one._id in ids
        assert institution_two._id in ids

    def test_institution_relationship_errors(self, app, user, user_two, institution_one, institution_two, url):

    # def test_type_mistyped(self):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'wow', 'id': institution_one._id}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 409

    # def test_post_with_auth(self):
        res = app.post_json_api(
            url, {},
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    # def test_put_with_auth(self):
        res = app.put_json_api(
            url, {},
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    # def test_post_without_auth(self):
        res = app.post_json_api(
            url, {}, expect_errors=True
        )

        assert res.status_code == 401

    # def test_put_without_auth(self):
        res = app.put_json_api(
            url, {}, expect_errors=True
        )

        assert res.status_code == 401

    # def test_delete_no_auth(self):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id}
            ]},
            expect_errors=True
        )

        assert res.status_code == 401

    # def test_delete_wrong_auth(self):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id}
            ]},
            auth=user_two.auth, expect_errors=True
        )

        assert res.status_code == 403

    # def test_attempt_payload_not_in_array(self):
        res = app.delete_json_api(
            url,
            {'data':
                {'type': 'institutions', 'id': institution_one._id}
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    # def test_attempt_with_no_type_field(self):
        res = app.delete_json_api(
            url,
            {'data': [
                {'id': institution_one._id}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    # def test_attempt_with_no_id_field(self):
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions'}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400
