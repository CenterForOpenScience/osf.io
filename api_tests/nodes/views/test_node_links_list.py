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
    AuthUserFactory,
    RetractedRegistrationFactory
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

    def test_return_embedded_public_node_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

    def test_return_embedded_public_node_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

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
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.pointer_project._id)

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

    def test_cannot_access_retracted_node_links_list(self):
        registration = RegistrationFactory(creator=self.user, project=self.public_project)
        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        retraction = RetractedRegistrationFactory(registration=registration, user=registration.creator)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


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
        assert_equal(res.status_code, 400)

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
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

    def test_creates_private_node_pointer_logged_out(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        res_json = res.json['data']
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.pointer_project._id)
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
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.user_two_project._id)

    def test_create_pointer_non_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_create_pointer_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
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
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_project._id)

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
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

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
        assert_equal(res.status_code, 404)

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


class TestNodeLinksBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeLinksBulkCreate, self).setUp()
        self.user = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_pointer_project_two = ProjectFactory(is_public=False, creator=self.user)

        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.private_project._id)

        self.private_payload = {
            'data': [{
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            "id": self.private_pointer_project._id,
                            "type": 'nodes'
                        }
                    }

                }
            },
            {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            "id": self.private_pointer_project_two._id,
                            "type": 'nodes'
                        }
                    }

                }
            }]
        }

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project_two = ProjectFactory(is_public=True, creator=self.user)

        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)
        self.public_payload = {
            'data': [{
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            "id": self.public_pointer_project._id,
                            "type": 'nodes'
                        }
                    }

                }
            },
            {
                "type": "node_links",
                "relationships": {
                    'nodes': {
                        'data': {
                            "id": self.public_pointer_project_two._id,
                            "type": 'nodes'
                        }
                    }

                }
            }]
        }

        self.user_two = AuthUserFactory()
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.user_two_project._id)
        self.user_two_payload = {'data': [{
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
    ]}

    def test_bulk_create_node_links_blank_request(self):
        res = self.app.post_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_creates_pointers_limits(self):
        payload = {'data': [self.public_payload['data'][0]] * 101}
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

        res = self.app.get(self.public_url)
        assert_equal(res.json['data'], [])

    def test_bulk_creates_project_target_not_nested(self):
        payload = {'data': [{'type': 'node_links', 'target_node_id': self.private_pointer_project._id}]}
        res = self.app.post_json_api(self.public_url, payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')

    def test_bulk_creates_public_node_pointers_logged_out(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

        res = self.app.get(self.public_url)
        assert_equal(res.json['data'], [])

    def test_bulk_creates_public_node_pointer_logged_in_non_contrib(self):
        res = self.app.post_json_api(self.public_url, self.public_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_bulk_creates_public_node_pointer_logged_in_contrib(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

        embedded = res_json[1]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project_two._id)


    def test_bulk_creates_private_node_pointers_logged_out(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    @assert_logs(NodeLog.POINTER_CREATED, 'private_project', index=-1)
    @assert_logs(NodeLog.POINTER_CREATED, 'private_project')
    def test_bulk_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.private_pointer_project._id)

        embedded = res_json[1]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.private_pointer_project_two._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_bulk_creates_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_bulk_creates_node_pointers_non_contributing_node_to_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'private_project')
    def test_bulk_creates_node_pointers_contributing_node_to_non_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.user_two_project._id)

        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.user_two_project._id)

    def test_bulk_creates_pointers_non_contributing_node_to_fake_node(self):
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = self.app.post_json_api(self.private_url, fake_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_creates_pointers_contributing_node_to_fake_node(self):
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = self.app.post_json_api(self.private_url, fake_payload,
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_creates_fake_nodes_pointing_to_contributing_node(self):
        fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'fdxlq')

        res = self.app.post_json_api(fake_url, self.private_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(fake_url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_bulk_creates_node_pointer_to_itself(self):
        point_to_itself_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.public_project._id}}}}]}

        res = self.app.post_json_api(self.public_url, point_to_itself_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_project._id)

    def test_bulk_creates_node_pointer_to_itself_unauthorized(self):
        point_to_itself_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.public_project._id}}}}]}

        res = self.app.post_json_api(self.public_url, point_to_itself_payload, bulk=True, auth=self.user_two.auth,
                                     expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    @assert_logs(NodeLog.POINTER_CREATED, 'public_project', index=-1)
    def test_bulk_creates_node_pointer_already_connected(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.public_pointer_project._id)

        embedded_two = res_json[1]['embeds']['target_node']['data']['id']
        assert_equal(embedded_two, self.public_pointer_project_two._id)

        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_in("Target Node '{}' already pointed to by '{}'.".format(self.public_pointer_project._id, self.public_project._id), res.json['errors'][0]['detail'])

    def test_bulk_cannot_add_link_to_registration(self):
        registration = RegistrationFactory(creator=self.user)

        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.public_pointer_project._id}}}}]}
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)

    def test_bulk_creates_node_pointer_no_type(self):
        payload = {'data': [{'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.user_two_project._id}}}}]}
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')

    def test_bulk_creates_node_pointer_incorrect_type(self):
        payload = {'data': [{'type': 'Wrong type.', 'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.user_two_project._id}}}}]}
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')


class TestBulkDeleteNodeLinks(ApiTestCase):

    def setUp(self):
        super(TestBulkDeleteNodeLinks, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True)
        self.pointer_project_two = ProjectFactory(creator=self.user, is_public=True)

        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.pointer_two = self.project.add_pointer(self.pointer_project_two, auth=Auth(self.user), save=True)

        self.private_payload = {
              "data": [
                {"type": "node_links", "id": self.pointer._id},
                {"type": "node_links", "id": self.pointer_two._id}
              ]
            }

        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project_two = ProjectFactory(is_public=True, creator=self.user)

        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_pointer_two = self.public_project.add_pointer(self.public_pointer_project_two,
                                                              auth=Auth(self.user),
                                                              save=True)

        self.public_payload = {
              'data': [
                {'type': 'node_links', 'id': self.public_pointer._id},
                {'type': 'node_links', 'id': self.public_pointer_two._id}
              ]
            }

        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)

    def test_bulk_delete_node_links_blank_request(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_pointer_limits(self):
        res = self.app.delete_json_api(self.public_url, {'data': [self.public_payload['data'][0]] * 101},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.public_url, {'data': {'id': self.public_project._id, 'type': 'node_links'}},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_pointers_no_type(self):
        payload = {'data': [
            {'id': self.public_pointer._id},
            {'id': self.public_pointer_two._id}
        ]}
        res = self.app.delete_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], "/data/type")

    def test_bulk_delete_pointers_incorrect_type(self):
        payload = {'data': [
            {'id': self.public_pointer._id, 'type': 'Incorrect type.'},
            {'id': self.public_pointer_two._id, 'type': 'Incorrect type.'}
        ]}
        res = self.app.delete_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_pointers_no_id(self):
        payload = {'data': [
            {'type': 'node_links'},
            {'type': 'node_links'}
        ]}
        res = self.app.delete_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], "/data/id")

    def test_bulk_delete_pointers_no_data(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must contain array of resource identifier objects.')

    def test_bulk_delete_pointers_payload_is_empty_dict(self):
        res = self.app.delete_json_api(self.public_url, {}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')

    def test_cannot_delete_if_registration(self):
        registration = RegistrationFactory(project=self.public_project)

        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)

        res = self.app.delete_json_api(url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)

    def test_bulk_deletes_public_node_pointers_logged_out(self):
        res = self.app.delete_json_api(self.public_url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_deletes_public_node_pointers_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete_json_api(self.public_url, self.public_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])
        self.public_project.reload()
        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project', index=-1)
    def test_bulk_deletes_public_node_pointers_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete_json_api(self.public_url, self.public_payload, auth=self.user.auth, bulk=True)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 2, len(self.public_project.nodes_pointer))

        self.public_project.reload()

    def test_bulk_deletes_private_node_pointers_logged_out(self):
        res = self.app.delete_json_api(self.private_url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'project', index=-1)
    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_bulk_deletes_private_node_pointers_logged_in_contributor(self):
        res = self.app.delete_json_api(self.private_url, self.private_payload, auth=self.user.auth, bulk=True)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)

    def test_bulk_deletes_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.delete_json_api(self.private_url, self.private_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project', index=-1)
    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_return_bulk_deleted_public_node_pointer(self):
        res = self.app.delete_json_api(self.public_url, self.public_payload, auth=self.user.auth, bulk=True)
        self.public_project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        pointer_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

        #check that deleted pointer can not be returned
        res = self.app.get(pointer_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.POINTER_REMOVED, 'project', index=-1)
    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_return_bulk_deleted_private_node_pointer(self):
        res = self.app.delete_json_api(self.private_url, self.private_payload, auth=self.user.auth, bulk=True)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        pointer_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.project._id, self.pointer._id)

        #check that deleted pointer can not be returned
        res = self.app.get(pointer_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_bulk_delete_link_that_is_not_linked_to_correct_node(self):
        project = ProjectFactory(creator=self.user)
        # The node link belongs to a different project
        res = self.app.delete_json_api(
            self.private_url, self.public_payload,
            auth=self.user.auth,
            expect_errors=True,
            bulk=True
        )
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Node link does not belong to the requested node.')

