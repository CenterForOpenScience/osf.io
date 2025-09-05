from unittest import mock
import pytest
from rest_framework import exceptions

from api.base.settings.defaults import API_BASE
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache
from api_tests.nodes.views.utils import NodeCRUDTestCase
from api_tests.subjects.mixins import UpdateSubjectsMixin
from framework.auth.core import Auth
from osf.models import NodeLog, NotificationType
from osf.utils.sanitize import strip_html
from osf.utils import permissions
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    PreprintFactory,
    IdentifierFactory,
)
from tests.base import fake
from tests.utils import assert_latest_log, assert_latest_log_not, assert_notification, capture_notifications
from website import settings


@pytest.mark.django_db
class TestNodeUpdate(NodeCRUDTestCase):

    def test_node_institution_update(self, app, user_two, project_private, url_private, make_node_payload,
                                     institution_one, institution_two):
        project_private.add_contributor(
            user_two,
            permissions=permissions.ADMIN,
            auth=Auth(project_private.creator)
        )
        affiliated_institutions = {
            'affiliated_institutions':
                {'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    },
                    {
                        'type': 'institutions',
                        'id': institution_two._id
                    },
                ]
                }
        }
        with assert_notification(type=NotificationType.Type.NODE_AFFILIATION_CHANGED, user=user_two, times=2):
            res = app.patch_json_api(
                url_private,
                make_node_payload(
                    project_private,
                    {'public': False},
                    relationships=affiliated_institutions
                ),
                auth=user_two.auth,
                expect_errors=False
            )
        assert res.status_code == 200
        institutions = project_private.affiliated_institutions.all()
        assert institution_one in institutions
        assert institution_two in institutions

    def test_node_update_invalid_data(self, app, user, url_public):
        res = app.put_json_api(
            url_public, 'Incorrect data',
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

        res = app.put_json_api(
            url_public, ['Incorrect data'],
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_cannot_make_project_public_if_non_contributor(self, app, project_private, url_private, make_node_payload):
        with assert_latest_log_not(NodeLog.MADE_PUBLIC, project_private):
            non_contrib = AuthUserFactory()
            res = app.patch_json(
                url_private,
                make_node_payload(project_private, {'public': True}),
                auth=non_contrib.auth, expect_errors=True
            )
            assert res.status_code == 403

    def test_cannot_make_project_public_if_non_admin_contributor(
            self, app, project_private, url_private, make_node_payload):
        non_admin = AuthUserFactory()
        project_private.add_contributor(
            non_admin,
            permissions=permissions.WRITE,
            auth=Auth(project_private.creator),
            notification_type=False
        )
        project_private.save()
        res = app.patch_json(
            url_private,
            make_node_payload(project_private, {'public': True}),
            auth=non_admin.auth, expect_errors=True
        )
        assert res.status_code == 403

        project_private.reload()
        assert not project_private.is_public

    def test_can_make_project_public_if_admin_contributor(
            self, app, project_private, url_private, make_node_payload):
        with assert_latest_log(NodeLog.MADE_PUBLIC, project_private):
            admin_user = AuthUserFactory()
            project_private.add_contributor(
                admin_user,
                permissions=permissions.ADMIN,
                auth=Auth(project_private.creator),
                notification_type=False
            )
            project_private.save()
            with capture_notifications():
                res = app.patch_json_api(
                    url_private,
                    make_node_payload(project_private, {'public': True}),
                    auth=admin_user.auth  # self.user is creator/admin
                )
            assert res.status_code == 200
            project_private.reload()
            assert project_private.is_public

    def test_make_project_private_uncalculated_storage_limit(
        self, app, url_public, project_public, user
    ):
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.delete(key)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This project\'s node storage usage could not be calculated. Please try again.'

    def test_make_project_private_over_storage_limit(
        self, app, url_public, project_public, user
    ):
        # If the public node exceeds the the private storage limit
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE + 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This project exceeds private project storage limits and thus cannot be converted into a private project.'

    def test_make_project_private_under_storage_limit(
        self, app, url_public, project_public, user
    ):
        # If the public node does not exceed the private storage limit
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE - 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is False

    def test_update_errors(
            self, app, user, user_two, title_new, description_new,
            category_new, project_public, project_private,
            url_public, url_private):

        #   test_update_project_properties_not_nested
        res = app.put_json_api(url_public, {
            'id': project_public._id,
            'type': 'nodes',
            'title': title_new,
            'description': description_new,
            'category': category_new,
            'public': True,
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        #   test_update_invalid_id
        res = app.put_json_api(url_public, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_invalid_type
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'node',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_no_id
        res = app.put_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_update_no_type
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_update_public_project_logged_out
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_update_project_invalid_title
        project = {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'title': 'A' * 513,
                    'category': 'project',
                }
            }
        }
        res = app.put_json_api(
            url_public, project,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Title cannot exceed 512 characters.'

    #   test_update_public_project_logged_in_but_unauthorized
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_update_private_project_logged_out
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_update_private_project_logged_in_non_contributor
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_update_public_project_logged_in(
            self, app, user, title_new, description_new,
            category_new, project_public, url_public):
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == title_new
        assert res.json['data']['attributes']['description'] == description_new
        assert res.json['data']['attributes']['category'] == category_new
        log_actions = project_public.logs.values_list('action', flat=True)
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_cannot_update_a_registration(self, app, user, project_public):
        registration = RegistrationFactory(
            project=project_public, creator=user)
        original_title = registration.title
        original_description = registration.description
        url = f'/{API_BASE}nodes/{registration._id}/'
        res = app.put_json_api(url, {
            'data': {
                'id': registration._id,
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'hypothesis',
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        registration.reload()
        assert res.status_code == 404
        assert registration.title == original_title
        assert registration.description == original_description

    def test_update_private_project_logged_in_contributor(
            self, app, user, title_new, description_new,
            category_new, project_private, url_private):
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == title_new
        assert res.json['data']['attributes']['description'] == description_new
        assert res.json['data']['attributes']['category'] == category_new
        log_actions = [log.action for log in project_private.logs.all()]
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_update_project_sanitizes_html_properly(
            self, app, user, category_new, project_public, url_public):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'description': new_description,
                    'category': category_new,
                    'public': True,
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == strip_html(
            new_title)
        assert res.json['data']['attributes']['description'] == strip_html(
            new_description)
        log_actions = [log.action for log in project_public.logs.all()]
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(
            self, app, user, description, category, project_public, url_public):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_public):
            new_title = 'An <script>alert("even cooler")</script> project'
            res = app.patch_json_api(url_public, {
                'data': {
                    'id': project_public._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title
                    }
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'

            res = app.get(url_public)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == strip_html(
                new_title)
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_partial_update_public_project_logged_in(
        self, app, user, title_new, description, category, project_public, url_public
    ):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_public):
            res = app.patch_json_api(url_public, {
                'data': {
                    'id': project_public._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': title_new,
                    }
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_write_to_public_field_non_contrib_forbidden(
            self, app, user_two, project_public, url_public):
        # Test non-contrib writing to public field
        res = app.patch_json_api(url_public, {
            'data': {
                'attributes': {
                    'public': False},
                'id': project_public._id,
                'type': 'nodes'
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_errors(
            self, app, user, user_two, title_new,
            project_public, project_private,
            url_public, url_private):

        #   test_partial_update_public_project_logged_out
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_public_project_logged_in_but_unauthorized
        # Public resource, logged in, unauthorized
        res = app.patch_json_api(url_public, {
            'data': {
                'attributes': {
                    'title': title_new},
                'id': project_public._id,
                'type': 'nodes',
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_private_project_logged_out
        res = app.patch_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_private_project_logged_in_non_contributor
        res = app.patch_json_api(url_private, {
            'data': {
                'attributes': {
                    'title': title_new},
                'id': project_private._id,
                'type': 'nodes',
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_invalid_id
        res = app.patch_json_api(url_public, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                        'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_invalid_type
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'node',
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_no_id
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_partial_update_no_type
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   Nothing will be updated here
    #   test_partial_update_project_properties_not_nested
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'title': title_new,
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_partial_update_private_project_logged_in_contributor(
            self, app, user, title_new, description, category, project_private, url_private):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_private):
            res = app.patch_json_api(url_private, {
                'data': {
                    'attributes': {
                        'title': title_new},
                    'id': project_private._id,
                    'type': 'nodes',
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_multiple_patch_requests_with_same_category_generates_one_log(
            self, app, user, project_private, url_private, make_node_payload):
        project_private.category = 'project'
        project_private.save()
        new_category = 'data'
        payload = make_node_payload(
            project_private,
            attributes={'category': new_category})
        original_n_logs = project_private.logs.count()

        res = app.patch_json_api(url_private, payload, auth=user.auth)
        assert res.status_code == 200
        project_private.reload()
        assert project_private.category == new_category
        assert project_private.logs.count() == original_n_logs + 1  # sanity check

        app.patch_json_api(url_private, payload, auth=user.auth)
        project_private.reload()
        assert project_private.category == new_category
        assert project_private.logs.count() == original_n_logs + 1

    def test_public_project_with_publicly_editable_wiki_turns_private(
            self, app, user, project_public, url_public, make_node_payload):
        wiki = project_public.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=Auth(user=user), log=True)
        res = app.patch_json_api(
            url_public,
            make_node_payload(project_public, {'public': False}),
            auth=user.auth  # self.user is creator/admin
        )
        assert res.status_code == 200

    @mock.patch('osf.models.node.update_doi_metadata_on_change')
    def test_set_node_private_updates_doi(
            self, mock_update_doi_metadata, app, user, project_public,
            url_public, make_node_payload):

        IdentifierFactory(referent=project_public, category='doi')
        res = app.patch_json_api(
            url_public,
            make_node_payload(
                project_public,
                {'public': False}),
            auth=user.auth)
        assert res.status_code == 200
        project_public.reload()
        assert not project_public.is_public
        mock_update_doi_metadata.assert_called_with(project_public._id)

    @pytest.mark.enable_enqueue_task
    @mock.patch('website.preprints.tasks.update_or_enqueue_on_preprint_updated')
    def test_set_node_with_preprint_private_updates_doi(
            self, mock_update_doi_metadata, app, user,
            project_public, url_public, make_node_payload):
        target_object = PreprintFactory(project=project_public)

        res = app.patch_json_api(
            url_public,
            make_node_payload(
                project_public,
                {'public': False}),
            auth=user.auth)
        assert res.status_code == 200
        project_public.reload()
        assert not project_public.is_public
        # Turning supplemental_project private no longer turns preprint private
        assert target_object.is_public
        assert not mock_update_doi_metadata.called


@pytest.mark.django_db
class TestUpdateNodeSubjects(UpdateSubjectsMixin):

    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        project = ProjectFactory(is_public=True, creator=user_admin_contrib)
        project.add_contributor(user_write_contrib, permissions=permissions.WRITE)
        project.add_contributor(user_read_contrib, permissions=permissions.READ)
        project.save()
        return project
