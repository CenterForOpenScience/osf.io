# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
from urlparse import urlparse
from framework.auth.core import Auth

from website.models import NodeLog

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory
)
from tests.utils import assert_logs

node_url_for = lambda n_id: '/{}nodes/{}/'.format(API_BASE, n_id)


class TestNodeLinksList(ApiTestCase):

    def setUp(self):
        super(TestNodeLinksList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_node_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json[0]['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_return_public_node_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json[0]['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_return_private_node_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_private_node_pointers_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res_json), 1)
        expected_path = node_url_for(self.pointer_project._id)
        actual_path = urlparse(res_json[0]['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_return_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_deleted_links_not_returned(self):
        res = self.app.get(self.public_url, expect_errors=True)
        res_json = res.json['data']
        original_length = len(res_json)

        self.public_pointer_project.is_deleted = True
        self.public_pointer_project.save()

        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), original_length - 1)


class TestNodeLinkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeLinkCreate, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.private_payload = {
            'data': {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            'id': self.pointer_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)
        self.public_payload = {
            'data': {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            'id': self.public_pointer_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        self.fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'fdxlq')
        self.fake_payload = {
            'data': {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            'id': 'fdxlq',
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        self.point_to_itself_payload = {
            'data': {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            'id': self.public_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }

        self.user_two = AuthUserFactory()
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.user_two_project._id)
        self.user_two_payload = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }

    def test_add_node_link_relationships_is_a_list(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': [{'target_node_id': self.public_pointer_project._id}]
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_create_node_link_invalid_data(self):
        res = self.app.post_json_api(self.public_url, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")


    def test_add_node_link_no_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'attributes': {
                    'id': self.public_pointer_project._id
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

    def test_add_node_links_empty_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {}
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

    def test_add_node_links_no_nodes_key_in_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'data': {
                        'id': self.public_pointer_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Malformed request.')

    def test_add_node_links_no_data_in_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'id': self.public_pointer_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')

    def test_add_node_links_no_target_type_in_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.public_pointer_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')


    def test_add_node_links_no_target_id_in_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_add_node_links_incorrect_target_id_in_relationships(self):
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': '12345'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_add_node_links_incorrect_target_type_in_relationships(self):
        data = {
            'data': {
                'type': 'nodes',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'Incorrect!',
                            'id': self.public_pointer_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_creates_node_link_target_not_nested(self):
        payload = {
            'data': {
                'type': 'node_links',
                'id': self.pointer_project._id
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')

    def test_creates_public_node_pointer_logged_out(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_creates_public_node_pointer_logged_in(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_creates_private_node_pointer_logged_out(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        res_json = res.json['data']
        expected_path = node_url_for(self.pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_create_node_pointer_non_contributing_node_to_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'project')
    def test_create_node_pointer_contributing_node_to_non_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.user_two_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_create_pointer_non_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_create_pointer_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_create_fake_node_pointing_to_contributing_node(self):
        res = self.app.post_json_api(self.fake_url, self.private_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(self.fake_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_create_node_pointer_to_itself(self):
        res = self.app.post_json_api(self.public_url, self.point_to_itself_payload, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.public_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_create_node_pointer_to_itself_unauthorized(self):
        res = self.app.post_json_api(self.public_url, self.point_to_itself_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_create_node_pointer_already_connected(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.public_pointer_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])

    def test_cannot_add_link_to_registration(self):
        registration = RegistrationFactory(creator=self.user)

        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        payload = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.public_pointer_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_node_pointer_no_type(self):
        payload = {
            'data': {
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_node_pointer_incorrect_type(self):
        payload = {
            'data': {
                'type': 'Wrong type.',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': self.user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

