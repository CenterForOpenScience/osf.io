# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)


class TestExceptionFormatting(ApiTestCase):
    def setUp(self):

        super(TestExceptionFormatting, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.project_no_title = {
            'data': {
                'attributes': {
                    'description': self.description,
                    'category': self.category,
                    'type': 'nodes',
                }
            }
        }

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_creates_project_with_no_title_formatting(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.post_json_api(url, self.project_no_title, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/attributes/title'})
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')

    def test_node_does_not_exist_formatting(self):
        url = '/{}nodes/{}/'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'Not found.'})

    def test_forbidden_formatting(self):
        res = self.app.get(self.private_url, auth=self.non_contrib.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'You do not have permission to perform this action.'})

    def test_not_authorized_formatting(self):
        res = self.app.get(self.private_url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': "Authentication credentials were not provided."})

    def test_update_project_with_no_title_or_category_formatting(self):
        res = self.app.put_json_api(self.private_url, {'data': {'type': 'nodes', 'id': self.private_project._id, 'attributes': {'description': 'New description'}}}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(len(errors), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/attributes/category'}, {'pointer': '/data/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field is required.', 'This field is required.'])

    def test_create_node_link_no_target_formatting(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': '',
                            'type': 'nodes',
                        }
                    }
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/id'})
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')

    def test_node_link_already_exists(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.public_project._id,
                            'type': 'nodes',
                        }
                    }
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        res = self.app.post_json_api(url, {'data': {
            'type': 'node_links',
            'relationships': {
                'nodes': {
                    'data': {
                        'id': self.public_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.status_code, 400)
        assert(self.public_project._id in res.json['errors'][0]['detail'])
