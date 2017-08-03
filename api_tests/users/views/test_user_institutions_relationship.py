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

    def test_get(self, app, user, institution_one, institution_two, url):

    #   test_get_relationship_institutions
        res = app.get(
            url, auth=user.auth
        )

        assert res.status_code == 200

        assert user.absolute_api_v2_url + 'relationships/institutions/' in res.json['links']['self']
        assert user.absolute_api_v2_url + 'institutions/' in res.json['links']['html']

        ids = [val['id'] for val in res.json['data']]
        assert institution_one._id in ids
        assert institution_two._id in ids

    #   test_get_institutions_relationship_while_logged_out
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

    #   test_type_mistyped
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'wow', 'id': institution_one._id}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 409

    #   test_post_with_auth
        res = app.post_json_api(
            url, {},
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    #   test_put_with_auth
        res = app.put_json_api(
            url, {},
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    #   test_post_without_auth
        res = app.post_json_api(
            url, {}, expect_errors=True
        )

        assert res.status_code == 401

    #   test_put_without_auth
        res = app.put_json_api(
            url, {}, expect_errors=True
        )

        assert res.status_code == 401

    #   test_delete_no_auth
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id}
            ]},
            expect_errors=True
        )

        assert res.status_code == 401

    #   test_delete_wrong_auth
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions', 'id': institution_one._id}
            ]},
            auth=user_two.auth, expect_errors=True
        )

        assert res.status_code == 403

    #   test_attempt_payload_not_in_array
        res = app.delete_json_api(
            url,
            {'data':
                {'type': 'institutions', 'id': institution_one._id}
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_attempt_with_no_type_field
        res = app.delete_json_api(
            url,
            {'data': [
                {'id': institution_one._id}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_attempt_with_no_id_field
        res = app.delete_json_api(
            url,
            {'data': [
                {'type': 'institutions'}
            ]},
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400
