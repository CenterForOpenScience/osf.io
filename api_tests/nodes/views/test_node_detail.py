# -*- coding: utf-8 -*-
from urlparse import urlparse
from nose.tools import *  # flake8: noqa
import functools

from framework.auth.core import Auth
from modularodm import Q

from website.models import NodeLog
from website.views import find_bookmark_collection
from website.util import permissions
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    NodeLicenseRecordFactory,
)

from website.project.licenses import ensure_licenses
from website.project.licenses import NodeLicense

ensure_licenses = functools.partial(ensure_licenses, warn=False)

from tests.utils import assert_logs, assert_not_logs


class TestNodeDetail(ApiTestCase):
    def setUp(self):
        super(TestNodeDetail, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_component_url = '/{}nodes/{}/'.format(API_BASE, self.public_component._id)
        self.read_permissions = ['read']
        self.write_permissions = ['read', 'write']
        self.admin_permissions = ['read', 'admin', 'write']

    def test_return_public_project_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)
        assert_items_equal(res.json['data']['attributes']['current_user_permissions'], self.read_permissions)

    def test_return_public_project_details_contributor_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)
        assert_items_equal(res.json['data']['attributes']['current_user_permissions'], self.admin_permissions)

    def test_return_public_project_details_non_contributor_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)
        assert_items_equal(res.json['data']['attributes']['current_user_permissions'], self.read_permissions)

    def test_return_private_project_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_private_project_details_logged_in_admin_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.private_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.private_project.category)
        assert_items_equal(res.json['data']['attributes']['current_user_permissions'], self.admin_permissions)

    def test_return_private_project_details_logged_in_write_contributor(self):
        self.private_project.add_contributor(contributor=self.user_two, auth=Auth(self.user), save=True)
        res = self.app.get(self.private_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.private_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.private_project.category)
        assert_items_equal(res.json['data']['attributes']['current_user_permissions'], self.write_permissions)

    def test_return_private_project_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_top_level_project_has_no_parent(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_not_in('parent', res.json['data']['relationships'].keys())
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_child_project_has_parent(self):
        public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        public_component_url = '/{}nodes/{}/'.format(API_BASE, public_component._id)
        res = self.app.get(public_component_url)
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['parent']['links']['related']['href']
        assert_equal(urlparse(url).path, self.public_url)

    def test_node_has_children_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['children']['links']['related']['href']
        expected_url = self.public_url + 'children/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_contributors_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['contributors']['links']['related']['href']
        expected_url = self.public_url + 'contributors/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_node_links_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = self.public_url + 'node_links/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_registrations_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['registrations']['links']['related']['href']
        expected_url = self.public_url + 'registrations/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_files_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['files']['links']['related']['href']
        expected_url = self.public_url + 'files/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_comments_link(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_in('comments', res.json['data']['relationships'].keys())

    def test_node_has_correct_unread_comments_count(self):
        contributor = AuthUserFactory()
        self.public_project.add_contributor(contributor=contributor, auth=Auth(self.user), save=True)
        comment = CommentFactory(node=self.public_project, user=contributor, page='node')
        res = self.app.get(self.public_url + '?related_counts=True', auth=self.user.auth)
        unread = res.json['data']['relationships']['comments']['links']['related']['meta']['unread']
        unread_comments_node = unread['node']
        assert_equal(unread_comments_node, 1)

    def test_node_properties(self):
        res = self.app.get(self.public_url)
        assert_equal(res.json['data']['attributes']['public'], True)
        assert_equal(res.json['data']['attributes']['registration'], False)
        assert_equal(res.json['data']['attributes']['collection'], False)
        assert_equal(res.json['data']['attributes']['tags'], [])

    def test_requesting_folder_returns_error(self):
        folder = NodeFactory(is_collection=True, creator=self.user)
        res = self.app.get(
            '/{}nodes/{}/'.format(API_BASE, folder._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)

    def test_cannot_return_registrations_at_node_detail_endpoint(self):
        registration = RegistrationFactory(project=self.public_project, creator=self.user)
        res = self.app.get('/{}nodes/{}/'.format(API_BASE, registration._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_cannot_return_folder_at_node_detail_endpoint(self):
        folder = CollectionFactory(creator=self.user)
        res = self.app.get('/{}nodes/{}/'.format(API_BASE, folder._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


class NodeCRUDTestCase(ApiTestCase):

    def setUp(self):
        super(NodeCRUDTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'
        self.new_category = 'project'

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.fake_url = '/{}nodes/{}/'.format(API_BASE, '12345')


def make_node_payload(node, attributes):
    return {
        'data': {
            'id': node._id,
            'type': 'nodes',
            'attributes': attributes,
        }
    }


class TestNodeUpdate(NodeCRUDTestCase):

    def test_node_update_invalid_data(self):
        res = self.app.put_json_api(self.public_url, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.put_json_api(self.public_url, ["Incorrect data"], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    @assert_not_logs(NodeLog.MADE_PUBLIC, 'private_project')
    def test_cannot_make_project_public_if_non_contributor(self):
        non_contrib = AuthUserFactory()
        res = self.app.patch_json(
            self.private_url,
            make_node_payload(self.private_project, {'public': True}),
            auth=non_contrib.auth, expect_errors=True
        )
        assert_equal(res.status_code, 403)

    def test_cannot_make_project_public_if_non_admin_contributor(self):
        non_admin = AuthUserFactory()
        self.private_project.add_contributor(
            non_admin,
            permissions=(permissions.READ, permissions.WRITE),
            auth=Auth(self.private_project.creator)
        )
        self.private_project.save()
        res = self.app.patch_json(
            self.private_url,
            make_node_payload(self.private_project, {'public': True}),
            auth=non_admin.auth, expect_errors=True
        )
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_false(self.private_project.is_public)

    @assert_logs(NodeLog.MADE_PUBLIC, 'private_project')
    def test_can_make_project_public_if_admin_contributor(self):
        admin_user = AuthUserFactory()
        self.private_project.add_contributor(
            admin_user,
            permissions=(permissions.READ, permissions.WRITE, permissions.ADMIN),
            auth=Auth(self.private_project.creator)
        )
        self.private_project.save()
        res = self.app.patch_json_api(
            self.private_url,
            make_node_payload(self.private_project, {'public': True}),
            auth=admin_user.auth  # self.user is creator/admin
        )
        assert_equal(res.status_code, 200)
        self.private_project.reload()
        assert_true(self.private_project.is_public)

    def test_update_project_properties_not_nested(self):
        res = self.app.put_json_api(self.public_url, {
            'id': self.public_project._id,
            'type': 'nodes',
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_update_invalid_id(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_invalid_type(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'node',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_no_id(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_update_no_type(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_update_public_project_logged_out(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_update_public_project_logged_in(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_public_project_logged_in_but_unauthorized(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_cannot_update_a_registration(self):
        registration = RegistrationFactory(project=self.public_project, creator=self.user)
        original_title = registration.title
        original_description = registration.description
        url = '/{}nodes/{}/'.format(API_BASE, registration._id)
        res = self.app.put_json_api(url, {
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
        }, auth=self.user.auth, expect_errors=True)
        registration.reload()
        assert_equal(res.status_code, 404)
        assert_equal(registration.title, original_title)
        assert_equal(registration.description, original_description)

    def test_update_private_project_logged_out(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'private_project')
    def test_update_private_project_logged_in_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_private_project_logged_in_non_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_update_project_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'description': new_description,
                    'category': self.new_category,
                    'public': True,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(new_description))

    @assert_logs(NodeLog.EDITED_TITLE, 'public_project')
    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        res = self.app.patch_json_api(self.public_url, {
            'data': {
            'id': self.public_project._id,
            'type': 'nodes',
                'attributes': {
                    'title': new_title
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_write_to_public_field_non_contrib_forbidden(self):
        # Test non-contrib writing to public field
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'attributes': {
                    'public': False},
                'id': self.public_project._id,
                'type': 'nodes'
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_partial_update_public_project_logged_out(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.EDITED_TITLE, 'public_project')
    def test_partial_update_public_project_logged_in(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                'title': self.new_title,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_public_project_logged_in_but_unauthorized(self):
        # Public resource, logged in, unauthorized
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.public_project._id,
                'type': 'nodes',
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_partial_update_private_project_logged_out(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.EDITED_TITLE, 'private_project')
    def test_partial_update_private_project_logged_in_contributor(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.private_project._id,
                'type': 'nodes',
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_private_project_logged_in_non_contributor(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.private_project._id,
                'type': 'nodes',
            }
        }, auth=self.user_two.auth,expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_multiple_patch_requests_with_same_category_generates_one_log(self):
        self.private_project.category = 'project'
        self.private_project.save()
        new_category = 'data'
        payload = make_node_payload(self.private_project, attributes={'category': new_category})
        original_n_logs = len(self.private_project.logs)

        res = self.app.patch_json_api(self.private_url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.private_project.reload()
        assert_equal(self.private_project.category, new_category)
        assert_equal(len(self.private_project.logs), original_n_logs + 1)  # sanity check

        res = self.app.patch_json_api(self.private_url, payload, auth=self.user.auth)
        self.private_project.reload()
        assert_equal(self.private_project.category, new_category)
        assert_equal(len(self.private_project.logs), original_n_logs + 1)

    def test_partial_update_invalid_id(self):
        res = self.app.patch_json_api(self.public_url, {
                'data': {
                    'id': '12345',
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                    }
                }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_invalid_type(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'node',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_no_id(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_partial_update_no_type(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    # Nothing will be updated here
    def test_partial_update_project_properties_not_nested(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'title': self.new_title,
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_project_invalid_title(self):
        project = {
            'data': {
                'type': 'nodes',
                'id': self.public_project._id,
                'attributes': {
                    'title': 'A' * 201,
                    'category': 'project',
                }
            }
        }
        res = self.app.put_json_api(self.public_url, project, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')

    def test_public_project_with_publicly_editable_wiki_turns_private(self):
        wiki = self.public_project.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=Auth(user=self.user), log=True)
        res = self.app.patch_json_api(
            self.public_url,
            make_node_payload(self.public_project, {'public': False}),
            auth=self.user.auth  # self.user is creator/admin
        )
        assert_equal(res.status_code, 200)


class TestNodeDelete(NodeCRUDTestCase):

    def test_deletes_public_node_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_requesting_deleted_returns_410(self):
        self.public_project.is_deleted = True
        self.public_project.save()
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 410)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_public_node_fails_if_unauthorized(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.public_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.PROJECT_DELETED, 'public_project')
    def test_deletes_public_node_succeeds_as_owner(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.public_project.is_deleted, True)

    def test_deletes_private_node_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.PROJECT_DELETED, 'private_project')
    def test_deletes_private_node_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.private_project.is_deleted, True)

    def test_deletes_private_node_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.private_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_read_only_contributor(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ])
        self.private_project.save()
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.private_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_invalid_node(self):
        res = self.app.delete(self.fake_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_delete_project_with_component_returns_error(self):
        project = ProjectFactory(creator=self.user)
        component = NodeFactory(parent=project, creator=self.user)
        # Return a 400 because component must be deleted before deleting the parent
        res = self.app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, project._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(
            errors[0]['detail'],
            'Any child components must be deleted prior to deleting this project.'
        )

    def test_delete_bookmark_collection_returns_error(self):
        bookmark_collection = find_bookmark_collection(self.user)
        res = self.app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, bookmark_collection._id),
            auth=self.user.auth,
            expect_errors=True
        )
        # Bookmark collections are collections, so a 404 is returned
        assert_equal(res.status_code, 404)


class TestReturnDeletedNode(ApiTestCase):
    def setUp(self):

        super(TestReturnDeletedNode, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.public_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                             title='This public project has been deleted', category='project',
                                             is_public=True)
        self.private_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                              title='This private project has been deleted', category='project',
                                              is_public=False)
        self.private = ProjectFactory(is_public=False, creator=self.user, title='A boring project', category='project')
        self.public = ProjectFactory(is_public=True, creator=self.user, title='A fun project', category='project')

        self.new_title = 'This deleted node has been edited'

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_deleted._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_deleted._id)

    def test_return_deleted_public_node(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_return_deleted_private_node(self):
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_public_node(self):
        res = self.app.put_json_api(self.public_url, params={'title': self.new_title,
                                                    'node_id': self.public_deleted._id,
                                                    'category': self.public_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_private_node(self):
        res = self.app.put_json_api(self.private_url, params={'title': self.new_title,
                                                     'node_id': self.private_deleted._id,
                                                     'category': self.private_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_public_node(self):
        res = self.app.delete(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_private_node(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)


class TestNodeTags(ApiTestCase):
    def setUp(self):
        super(TestNodeTags, self).setUp()
        self.user = AuthUserFactory()
        self.admin = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.public_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.private_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.private_project.add_contributor(self.admin, permissions=permissions.CREATOR_PERMISSIONS, save=True)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.one_new_tag_json = {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }
        self.private_payload = {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    def test_public_project_starts_with_no_tags(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

    @assert_logs(NodeLog.TAG_ADDED, 'public_project')
    def test_contributor_can_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.public_project.reload()
        assert_equal(len(self.public_project.tags), 1)
        assert_equal(self.public_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.public_url)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    @assert_logs(NodeLog.TAG_ADDED, 'private_project')
    def test_contributor_can_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.private_project.reload()
        assert_equal(len(self.private_project.tags), 1)
        assert_equal(self.private_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    def test_partial_update_project_does_not_clear_tags(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, auth=self.admin.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        new_payload = {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'public': True
                }
            }
        }
        res = self.app.patch_json_api(self.private_url, new_payload, auth=self.admin.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        new_payload['data']['attributes']['public'] = False
        res = self.app.patch_json_api(self.private_url, new_payload, auth=self.admin.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)

    def test_non_authenticated_user_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_authenticated_user_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_non_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)\

    @assert_logs(NodeLog.TAG_ADDED, 'private_project', -4)
    @assert_logs(NodeLog.TAG_ADDED, 'private_project', -3)
    @assert_logs(NodeLog.TAG_REMOVED, 'private_project', -2)
    @assert_logs(NodeLog.TAG_REMOVED, 'private_project')
    def test_tags_add_and_remove_properly(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure adding tag data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure removing and adding tag data is correct from the PATCH response
        res = self.app.patch_json_api(self.private_url, {'data': {'id': self.private_project._id, 'type':'nodes', 'attributes': {'tags':['newer-tag']}}}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'newer-tag')
        # Ensure removing tag data is correct from the PATCH response
        res = self.app.patch_json_api(self.private_url, {'data': {'id': self.private_project._id, 'type':'nodes', 'attributes': {'tags': []}}}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

    def test_tags_post_object_instead_of_list(self):
        url = '/{}nodes/'.format(API_BASE)
        payload = {'data': {
            'type': 'nodes',
            'attributes': {
                'title': 'new title',
                'category': 'project',
                'tags': {'foo': 'bar'}
            }
        }}
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_tags_patch_object_instead_of_list(self):
        self.one_new_tag_json['data']['attributes']['tags'] = {'foo': 'bar'}
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')


class TestNodeLicense(ApiTestCase):
    def setUp(self):
        super(TestNodeLicense, self).setUp()
        self.user = AuthUserFactory()
        self.admin = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.public_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.private_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.private_project.add_contributor(self.admin, permissions=permissions.CREATOR_PERMISSIONS, save=True)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        ensure_licenses()
        self.LICENSE_NAME = 'MIT License'
        self.node_license = NodeLicense.find_one(
            Q('name', 'eq', self.LICENSE_NAME)
        )
        self.YEAR = '2105'
        self.COPYRIGHT_HOLDERS = ['Foo', 'Bar']
        self.public_project.node_license = NodeLicenseRecordFactory(
            node_license=self.node_license,
            year=self.YEAR,
            copyright_holders=self.COPYRIGHT_HOLDERS
        )
        self.public_project.save()
        self.private_project.node_license = NodeLicenseRecordFactory(
            node_license=self.node_license,
            year=self.YEAR,
            copyright_holders=self.COPYRIGHT_HOLDERS
        )
        self.private_project.save()

    def test_public_node_has_node_license(self):
        res = self.app.get(self.public_url)
        assert_equal(self.public_project.node_license.year, res.json['data']['attributes']['node_license']['year'])

    def test_public_node_has_license_relationship(self):
        res = self.app.get(self.public_url)
        expected_license_url = '/{}licenses/{}'.format(API_BASE, self.node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert_in(expected_license_url, actual_license_url)

    def test_private_node_has_node_license(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(self.private_project.node_license.year, res.json['data']['attributes']['node_license']['year'])

    def test_private_node_has_license_relationship(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        expected_license_url = '/{}licenses/{}'.format(API_BASE, self.node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert_in(expected_license_url, actual_license_url)