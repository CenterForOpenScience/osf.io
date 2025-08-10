import pytest

from api.base.settings.defaults import API_BASE
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache
from osf.models import NodeLog
from osf.utils import permissions
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
from tests.utils import assert_latest_log
from website import settings


@pytest.mark.django_db
class TestNodeTags:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user, user_admin):
        project_public = ProjectFactory(
            title='Project One', is_public=True, creator=user)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project_public

    @pytest.fixture()
    def project_private(self, user, user_admin):
        project_private = ProjectFactory(
            title='Project Two', is_public=False, creator=user)
        project_private.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True,
            notification_type=False
        )
        project_private.add_contributor(
            user,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True,
            notification_type=False
        )
        # Sets private project storage cache to avoid need for retries in tests updating public status
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_private._id)
        storage_usage_cache.set(key, 0, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return f'/{API_BASE}nodes/{project_public._id}/'

    @pytest.fixture()
    def url_private(self, project_private):
        return f'/{API_BASE}nodes/{project_private._id}/'

    @pytest.fixture()
    def payload_public(self, project_public):
        return {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    @pytest.fixture()
    def payload_private(self, project_private):
        return {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    def test_public_project_starts_with_no_tags(self, app, url_public):
        res = app.get(url_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    def test_node_detail_does_not_expose_system_tags(
            self, app, project_public, url_public):
        project_public.add_system_tag('systag', save=True)
        res = app.get(url_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    def test_contributor_can_add_tag_to_public_project(
            self, app, user, project_public, payload_public, url_public):
        with assert_latest_log(NodeLog.TAG_ADDED, project_public):
            res = app.patch_json_api(
                url_public,
                payload_public,
                auth=user.auth,
                expect_errors=True)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            project_public.reload()
            assert project_public.tags.count() == 1
            assert project_public.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_public)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

    def test_contributor_can_add_tag_to_private_project(
            self, app, user, project_private, payload_private, url_private):
        with assert_latest_log(NodeLog.TAG_ADDED, project_private):
            res = app.patch_json_api(
                url_private, payload_private, auth=user.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            project_private.reload()
            assert project_private.tags.count() == 1
            assert project_private.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_private, auth=user.auth)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

    def test_partial_update_project_does_not_clear_tags(
            self, app, user_admin, project_private, payload_private, url_private):
        res = app.patch_json_api(
            url_private,
            payload_private,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1
        new_payload = {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'public': True
                }
            }
        }
        res = app.patch_json_api(
            url_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1
        new_payload['data']['attributes']['public'] = False
        res = app.patch_json_api(
            url_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1

    def test_add_tag_to_project_errors(
            self, app, user_non_contrib, user_read_contrib,
            payload_public, payload_private,
            url_public, url_private):

        #   test_non_authenticated_user_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True, auth=None)
        assert res.status_code == 401

    #   test_non_authenticated_user_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True, auth=None)
        assert res.status_code == 401

    #   test_non_contributor_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True, auth=user_non_contrib.auth)
        assert res.status_code == 403

    #   test_non_contributor_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True, auth=user_non_contrib.auth)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True,
            auth=user_read_contrib.auth)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True,
            auth=user_read_contrib.auth)
        assert res.status_code == 403

    def test_tags_add_and_remove_properly(
            self, app, user, project_private,
            payload_private, url_private):
        with assert_latest_log(NodeLog.TAG_ADDED, project_private):
            res = app.patch_json_api(
                url_private, payload_private, auth=user.auth)
            assert res.status_code == 200
            # Ensure adding tag data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, project_private), assert_latest_log(NodeLog.TAG_ADDED, project_private, 1):
            # Ensure removing and adding tag data is correct from the PATCH
            # response
            res = app.patch_json_api(
                url_private,
                {
                    'data': {
                        'id': project_private._id,
                        'type': 'nodes',
                        'attributes': {'tags': ['newer-tag']}
                    }
                }, auth=user.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'newer-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, project_private):
            # Ensure removing tag data is correct from the PATCH response
            res = app.patch_json_api(
                url_private,
                {
                    'data': {
                        'id': project_private._id,
                        'type': 'nodes',
                        'attributes': {'tags': []}
                    }
                }, auth=user.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 0

    def test_tags_post_object_instead_of_list(self, user, app):
        url = f'/{API_BASE}nodes/'
        payload = {'data': {
            'type': 'nodes',
            'attributes': {
                'title': 'new title',
                'category': 'project',
                'tags': {'foo': 'bar'}
            }
        }}
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    def test_tags_patch_object_instead_of_list(
            self, app, user, payload_public, url_public):
        payload_public['data']['attributes']['tags'] = {'foo': 'bar'}
        res = app.patch_json_api(
            url_public, payload_public,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'
