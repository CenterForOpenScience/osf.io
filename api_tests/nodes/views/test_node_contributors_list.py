# -*- coding: utf-8 -*-
import random

import mock

import time

from nose.tools import *  # flake8: noqa

from rest_framework import exceptions

from unittest import TestCase

from api.base.exceptions import Conflict
from api.base.settings.defaults import API_BASE
from api.nodes.serializers import NodeContributorsCreateSerializer

from framework.auth.core import Auth

from tests.base import ApiTestCase, capture_signals, fake
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    UserFactory
)
from tests.utils import assert_logs

from website.models import NodeLog
from website.project.signals import contributor_added, unreg_contributor_added, contributor_removed
from website.util import permissions, disconnected_from_listeners

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

def make_contrib_id(node_id, user_id):
    return '{}-{}'.format(node_id, user_id)

class TestNodeContributorList(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorList, self).setUp()
        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    def test_concatenated_id(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)

        assert_equal(res.json['data'][0]['id'].split('-')[0], self.public_project._id)
        assert_equal(res.json['data'][0]['id'].split('-')[1], self.user._id)

    def test_permissions_work_with_many_users(self):
        users = {
            'admin': [self.user._id],
            'write': [],
            'read': []
        }
        for i in range(0, 25):
            perm = random.choice(users.keys())
            perms = []
            if perm == 'admin':
                perms = ['read', 'write', 'admin', ]
            elif perm == 'write':
                perms = ['read', 'write', ]
            elif perm == 'read':
                perms = ['read', ]
            user = AuthUserFactory()

            self.private_project.add_contributor(user, permissions=perms)
            users[perm].append(user._id)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        for user in data:
            api_perm = user['attributes']['permission']
            user_id = user['id'].split('-')[1]
            assert user_id in users[api_perm], 'Permissions incorrect for {}. Should not have {} permission.'.format(user_id, api_perm)

    def test_return_public_contributor_list_logged_out(self):
        self.public_project.add_contributor(self.user_two, save=True)

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], make_contrib_id(self.public_project._id, self.user._id))
        assert_equal(res.json['data'][1]['id'], make_contrib_id(self.public_project._id, self.user_two._id))

    def test_return_public_contributor_list_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], make_contrib_id(self.public_project._id, self.user._id))

    def test_return_private_contributor_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_contributor_list_logged_in_contributor(self):
        self.private_project.add_contributor(self.user_two)
        self.private_project.save()

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], make_contrib_id(self.private_project._id, self.user._id))
        assert_equal(res.json['data'][1]['id'], make_contrib_id(self.private_project._id, self.user_two._id))

    def test_return_private_contributor_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_filtering_on_obsolete_fields(self):
        # regression test for changes in filter fields
        url_fullname = '{}?filter[fullname]=foo'.format(self.public_url)
        res = self.app.get(url_fullname, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], u"'fullname' is not a valid field for this endpoint.")

        # middle_name is now middle_names
        url_middle_name = '{}?filter[middle_name]=foo'.format(self.public_url)
        res = self.app.get(url_middle_name, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'middle_name' is not a valid field for this endpoint.")

    def test_disabled_contributors_contain_names_under_meta(self):
        self.public_project.add_contributor(self.user_two, save=True)

        self.user_two.is_disabled = True
        self.user_two.save()

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], make_contrib_id(self.public_project._id, self.user._id))
        assert_equal(res.json['data'][1]['id'], make_contrib_id(self.public_project._id, self.user_two._id))
        assert_equal(res.json['data'][1]['embeds']['users']['errors'][0]['meta']['full_name'], self.user_two.fullname)
        assert_equal(res.json['data'][1]['embeds']['users']['errors'][0]['detail'], 'The requested user is no longer available.')

    def test_total_bibliographic_contributor_count_returned_in_metadata(self):
        non_bibliographic_user = UserFactory()
        self.public_project.add_contributor(non_bibliographic_user, visible=False, auth=Auth(self.public_project.creator))
        self.public_project.save()
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total_bibliographic'], len(self.public_project.visible_contributor_ids))

    def test_unregistered_contributor_field_is_null_if_account_claimed(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes'].get('unregistered_contributor'), None)

    def test_unregistered_contributors_show_up_as_name_associated_with_project(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        project.add_unregistered_contributor('Robert Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][1]['embeds']['users']['data']['attributes']['full_name'], 'Robert Jackson')
        assert_equal(res.json['data'][1]['attributes'].get('unregistered_contributor'), 'Robert Jackson')

        project_two = ProjectFactory(creator=self.user, is_public=True)
        project_two.add_unregistered_contributor('Bob Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project_two._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

        assert_equal(res.json['data'][1]['embeds']['users']['data']['attributes']['full_name'], 'Robert Jackson')
        assert_equal(res.json['data'][1]['attributes'].get('unregistered_contributor'), 'Bob Jackson')

    def test_contributors_order_is_the_same_over_multiple_requests(self):
        self.public_project.add_unregistered_contributor(
            'Robert Jackson',
            'robert@gmail.com',
            auth=Auth(self.user),
            save=True
        )

        for i in range(0,10):
            new_user = AuthUserFactory()
            if i%2 == 0:
                visible = True
            else:
                visible = False
            self.public_project.add_contributor(
                new_user,
                visible=visible,
                auth=Auth(self.public_project.creator),
                save=True
            )
        req_one = self.app.get("{}?page=2".format(self.public_url), auth=Auth(self.public_project.creator))
        req_two = self.app.get("{}?page=2".format(self.public_url), auth=Auth(self.public_project.creator))
        id_one = [item['id'] for item in req_one.json['data']]
        id_two = [item['id'] for item in req_two.json['data']]
        for a, b in zip(id_one, id_two):
            assert_equal(a, b)


class TestNodeContributorFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeContributorFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_filtering_full_name_field(self):
        url = '/{}nodes/{}/contributors/?filter[full_name]=Freddie'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'full_name' is not a valid field for this endpoint.")

    def test_filtering_permission_field(self):
        url = '/{}nodes/{}/contributors/?filter[permission]=admin'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes'].get('permission'), 'admin')

    def test_filtering_node_with_only_bibliographic_contributors(self):
        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)
        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_node_with_non_bibliographic_contributor(self):
        non_bibliographic_contrib = UserFactory()
        self.project.add_contributor(non_bibliographic_contrib, visible=False)
        self.project.save()

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)

        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0]['attributes'].get('bibliographic', None))

    def test_filtering_on_invalid_field(self):
        url = '/{}nodes/{}/contributors/?filter[invalid]=foo'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'invalid' is not a valid field for this endpoint.")


class TestNodeContributorAdd(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorAdd, self).setUp()

        self.private_url = '/{}nodes/{}/contributors/?send_email=false'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/?send_email=false'.format(API_BASE, self.public_project._id)

        self.user_three = AuthUserFactory()
        self.data_user_two = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id,
                        }
                    }
                }
            }
        }
        self.data_user_three = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_three._id,
                        }
                    }
                }
             }
        }

    def test_add_node_contributors_relationships_is_a_list(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': [{'contributor_id': self.user_three._id}]
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_contributor_create_invalid_data(self):
        res = self.app.post_json_api(self.public_url, "Incorrect data", auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.post_json_api(self.public_url, ["Incorrect data"], auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_add_contributor_no_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'A user ID or full name must be provided to add a contributor.')

    def test_add_contributor_empty_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {}
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'A user ID or full name must be provided to add a contributor.')

    def test_add_contributor_no_user_key_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'id': self.user_two._id,
                    'type': 'users'
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Malformed request.')

    def test_add_contributor_no_data_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'id': self.user_two._id
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')

    def test_add_contributor_no_target_type_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')


    def test_add_contributor_no_target_id_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'A user ID or full name must be provided to add a contributor.')

    def test_add_contributor_incorrect_target_id_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': '12345'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_add_contributor_no_type(self):
        data = {
            'data': {
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], "/data/type")

    def test_add_contributor_incorrect_type(self):
        data = {
             'data': {
                'type': 'Incorrect type',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_contributor_is_visible_by_default(self):
        del self.data_user_two['data']['attributes']['bibliographic']
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.public_project._id, self.user_two._id))

        self.public_project.reload()
        assert_in(self.user_two, self.public_project.contributors)
        assert_true(self.public_project.get_visible(self.user_two))

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_adds_bibliographic_contributor_public_project_admin(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.public_project._id, self.user_two._id))

        self.public_project.reload()
        assert_in(self.user_two, self.public_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_non_bibliographic_contributor_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project._id, self.user_two._id))
        assert_equal(res.json['data']['attributes']['bibliographic'], False)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_false(self.private_project.get_visible(self.user_two))

    def test_adds_contributor_public_project_non_admin(self):
        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user), save=True)
        res = self.app.post_json_api(self.public_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public_project.reload()
        assert_not_in(self.user_three, self.public_project.contributors.all())

    def test_adds_contributor_public_project_non_contributor(self):
        res = self.app.post_json_api(self.public_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_not_in(self.user_three, self.public_project.contributors.all())

    def test_adds_contributor_public_project_not_logged_in(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_not_in(self.user_two, self.public_project.contributors.all())

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_contributor_private_project_admin(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project._id, self.user_two._id))

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_contributor_without_bibliographic_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_admin_contributor_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': permissions.ADMIN
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project._id, self.user_two._id))

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE, permissions.ADMIN])

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_write_contributor_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': permissions.WRITE
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project._id, self.user_two._id))

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_read_contributor_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': permissions.READ
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project._id, self.user_two._id))

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ])

    def test_adds_invalid_permission_contributor_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': 'invalid',
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.private_project.reload()
        assert_not_in(self.user_two, self.private_project.contributors.all())

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_none_permission_contributor_private_project_admin_uses_default_permissions(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': None
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        for permission in permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS:
            assert_true(self.private_project.has_permission(self.user_two, permission))

    def test_adds_already_existing_contributor_private_project_admin(self):
        self.private_project.add_contributor(self.user_two, auth=Auth(self.user), save=True)
        self.private_project.reload()

        res = self.app.post_json_api(self.private_url, self.data_user_two,
                                 auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_adds_non_existing_user_private_project_admin(self):
        data = {
             'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': 'FAKE',
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        self.private_project.reload()
        assert_equal(len(self.private_project.contributors), 1)

    def test_adds_contributor_private_project_non_admin(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user))
        res = self.app.post_json_api(self.private_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_not_in(self.user_three, self.private_project.contributors.all())

    def test_adds_contributor_private_project_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_not_in(self.user_three, self.private_project.contributors.all())

    def test_adds_contributor_private_project_not_logged_in(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.private_project.reload()
        assert_not_in(self.user_two, self.private_project.contributors.all())

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_unregistered_contributor_with_fullname(self):
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'John Doe',
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['unregistered_contributor'], 'John Doe')
        assert_equal(res.json['data']['attributes']['email'], None)
        assert_in(res.json['data']['embeds']['users']['data']['id'],
                  self.public_project.contributors.values_list('guids___id', flat=True))

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_contributor_with_fullname_and_email_unregistered_user(self):
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'John Doe',
                    'email': 'john@doe.com'
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['unregistered_contributor'], 'John Doe')
        assert_equal(res.json['data']['attributes']['email'], 'john@doe.com')
        assert_equal(res.json['data']['attributes']['bibliographic'], True)
        assert_equal(res.json['data']['attributes']['permission'], permissions.WRITE)
        assert_in(
            res.json['data']['embeds']['users']['data']['id'],
            self.public_project.contributors.values_list('guids___id', flat=True)
        )

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_contributor_with_fullname_and_email_unregistered_user_set_attributes(self):
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'John Doe',
                    'email': 'john@doe.com',
                    'bibliographic': False,
                    'permission': permissions.READ
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['unregistered_contributor'], 'John Doe')
        assert_equal(res.json['data']['attributes']['email'], 'john@doe.com')
        assert_equal(res.json['data']['attributes']['bibliographic'], False)
        assert_equal(res.json['data']['attributes']['permission'], permissions.READ)
        assert_in(res.json['data']['embeds']['users']['data']['id'],
                  self.public_project.contributors.values_list('guids___id', flat=True))

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_contributor_with_fullname_and_email_registered_user(self):
        user = UserFactory()
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': user.fullname,
                    'email': user.username
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['unregistered_contributor'], None)
        assert_equal(res.json['data']['attributes']['email'], user.username)
        assert_in(res.json['data']['embeds']['users']['data']['id'],
                  self.public_project.contributors.values_list('guids___id', flat=True))

    def test_add_unregistered_contributor_already_contributor(self):
        name, email = fake.name(), fake.email()
        self.public_project.add_unregistered_contributor(auth=Auth(self.user), fullname=name, email=email)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Doesn\'t Matter',
                    'email': email
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '{} is already a contributor.'.format(name))

    def test_add_contributor_index_returned(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['index'], 1)

        res = self.app.post_json_api(self.public_url, self.data_user_three, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['index'], 2)

    def test_add_contributor_set_index_out_of_range(self):
        user_one = UserFactory()
        self.public_project.add_contributor(user_one, save=True)
        user_two = UserFactory()
        self.public_project.add_contributor(user_two, save=True)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'index': 4
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'],
                     '4 is not a valid contributor index for node with id {}'.format(self.public_project._id))

    def test_add_contributor_set_index_first(self):
        user_one = UserFactory()
        self.public_project.add_contributor(user_one, save=True)
        user_two = UserFactory()
        self.public_project.add_contributor(user_two, save=True)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'index': 0
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        contributor_obj = self.public_project.contributor_set.get(user=self.user_two)
        index = list(self.public_project.get_contributor_order()).index(contributor_obj.pk)
        assert_equal(index, 0)

    def test_add_contributor_set_index_last(self):
        user_one = UserFactory()
        self.public_project.add_contributor(user_one, save=True)
        user_two = UserFactory()
        self.public_project.add_contributor(user_two, save=True)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'index': 3
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 201)
        contributor_obj = self.public_project.contributor_set.get(user=self.user_two)
        index = list(self.public_project.get_contributor_order()).index(contributor_obj.pk)
        assert_equal(index, 3)

    def test_add_inactive_merged_user_as_contributor(self):
        primary_user = UserFactory()
        merged_user = UserFactory(merged_by=primary_user)

        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {},
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': merged_user._id
                        }
                    }
                }
            }
        }

        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        contributor_added = res.json['data']['embeds']['users']['data']['id']
        assert_equal(contributor_added, primary_user._id)


class TestNodeContributorCreateValidation(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorCreateValidation, self).setUp()
        self.validate_data = NodeContributorsCreateSerializer.validate_data

    def test_add_contributor_validation_user_id(self):
        self.validate_data(NodeContributorsCreateSerializer(), self.public_project, user_id='abcde')

    def test_add_contributor_validation_user_id_fullname(self):
        with assert_raises(Conflict):
            self.validate_data(NodeContributorsCreateSerializer(), 'fake', user_id='abcde', full_name='Kanye')

    def test_add_contributor_validation_user_id_email(self):
        with assert_raises(Conflict):
            self.validate_data(NodeContributorsCreateSerializer(), 'fake', user_id='abcde', email='kanye@west.com')

    def test_add_contributor_validation_user_id_fullname_email(self):
        with assert_raises(Conflict):
            self.validate_data(NodeContributorsCreateSerializer(), 'fake', user_id='abcde', full_name='Kanye', email='kanye@west.com')

    def test_add_contributor_validation_fullname(self):
        self.validate_data(NodeContributorsCreateSerializer(), self.public_project, full_name='Kanye')

    def test_add_contributor_validation_email(self):
        with assert_raises(exceptions.ValidationError):
            self.validate_data(NodeContributorsCreateSerializer(), 'fake', email='kanye@west.com')

    def test_add_contributor_validation_fullname_email(self):
        self.validate_data(NodeContributorsCreateSerializer(), self.public_project, full_name='Kanye', email='kanye@west.com')


class TestNodeContributorCreateEmail(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorCreateEmail, self).setUp()
        self.url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_no_email_if_false(self, mock_mail):
        url = '{}?send_email=false'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_sends_email(self, mock_mail):
        url = '{}?send_email=default'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }

        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(mock_mail.call_count, 1)

    @mock.patch('website.project.signals.contributor_added.send')
    def test_add_contributor_signal_if_default(self, mock_send):
        url = '{}?send_email=default'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        args, kwargs = mock_send.call_args
        assert_equal(res.status_code, 201)
        assert_equal('default', kwargs['email_template'])

    @mock.patch('website.project.signals.contributor_added.send')
    def test_add_contributor_signal_if_preprint(self, mock_send):
        url = '{}?send_email=preprint'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        args, kwargs = mock_send.call_args
        assert_equal(res.status_code, 201)
        assert_equal('preprint', kwargs['email_template'])

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_sends_email(self, mock_mail):
        url = '{}?send_email=default'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(mock_mail.call_count, 1)

    @mock.patch('website.project.signals.unreg_contributor_added.send')
    def test_add_unregistered_contributor_signal_if_default(self, mock_send):
        url = '{}?send_email=default'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        args, kwargs = mock_send.call_args
        assert_equal(res.status_code, 201)
        assert_equal('default', kwargs['email_template'])

    @mock.patch('website.project.signals.unreg_contributor_added.send')
    def test_add_unregistered_contributor_signal_if_preprint(self, mock_send):
        url = '{}?send_email=preprint'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        args, kwargs = mock_send.call_args
        assert_equal(res.status_code, 201)
        assert_equal('preprint', kwargs['email_template'])

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_invalid_send_email_param(self, mock_mail):
        url = '{}?send_email=true'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'true is not a valid email preference.')
        assert_equal(mock_mail.call_count, 0)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_without_email_no_email(self, mock_mail):
        url = '{}?send_email=default'.format(self.url)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                }
            }
        }

        with capture_signals() as mock_signal:
            res = self.app.post_json_api(url, payload, auth=self.user.auth)
        assert_in(contributor_added, mock_signal.signals_sent())
        assert_equal(res.status_code, 201)
        assert_equal(mock_mail.call_count, 0)


class TestNodeContributorBulkCreate(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorBulkCreate, self).setUp()
        self.user_three = AuthUserFactory()

        self.private_url = '/{}nodes/{}/contributors/?send_email=false'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/?send_email=false'.format(API_BASE, self.public_project._id)

        self.payload_one = {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                    'permission': "admin"
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_two._id,
                            'type': 'users'
                        }
                    }
                }
        }

        self.payload_two = {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False,
                    'permission': "read"
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': self.user_three._id,
                            'type': 'users'
                        }
                    }
                }
        }

    def test_bulk_create_contributors_blank_request(self):
        res = self.app.post_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_node_contributor_bulk_create_contributor_exists(self):
        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        res = self.app.post_json_api(self.public_url, {'data': [self.payload_two, self.payload_one]},
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert 'is already a contributor' in res.json['errors'][0]['detail']

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

    def test_node_contributor_bulk_create_logged_out_public_project(self):
        res = self.app.post_json_api(self.public_url, {'data': [self.payload_one, self.payload_two]},
                                     expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_contributor_bulk_create_logged_in_public_project_project(self):
        res = self.app.post_json_api(self.public_url, {'data': [self.payload_one, self.payload_two]},
                                     auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_items_equal([res.json['data'][0]['attributes']['bibliographic'], res.json['data'][1]['attributes']['bibliographic']],
                           [True, False])
        assert_items_equal([res.json['data'][0]['attributes']['permission'], res.json['data'][1]['attributes']['permission']],
                           ['admin', 'read'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_node_contributor_bulk_create_logged_out_private_project(self):
        res = self.app.post_json_api(self.private_url, {'data': [self.payload_one, self.payload_two]},
                                     expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_contributor_bulk_create_logged_in_contrib_private_project(self):
        res = self.app.post_json_api(self.private_url, {'data': [self.payload_one, self.payload_two]},
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_items_equal([res.json['data'][0]['attributes']['bibliographic'], res.json['data'][1]['attributes']['bibliographic']],
                           [True, False])
        assert_items_equal([res.json['data'][0]['attributes']['permission'], res.json['data'][1]['attributes']['permission']],
                           ['admin', 'read'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_node_contributor_bulk_create_logged_in_non_contrib_private_project(self):
        res = self.app.post_json_api(self.private_url, {'data': [self.payload_one, self.payload_two]},
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_contributor_bulk_create_logged_in_read_only_contrib_private_project(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.post_json_api(self.private_url, {'data': [self.payload_two]},
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_contributor_bulk_create_all_or_nothing(self):
        invalid_id_payload = {
            'type': 'contributors',
            'attributes': {
                'bibliographic': True
            },
            'relationships': {
                'users': {
                    'data': {
                        'type': 'users',
                        'id': '12345'
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, {'data': [self.payload_one, invalid_id_payload]},
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_contributor_bulk_create_limits(self):
        node_contrib_create_list = {'data': [self.payload_one] * 101}
        res = self.app.post_json_api(self.public_url, node_contrib_create_list,
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_node_contributor_ugly_payload(self):
        payload = 'sdf;jlasfd'
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Malformed request.')

    def test_node_contributor_bulk_create_invalid_permissions_all_or_nothing(self):
        payload = {
            'type': 'contributors',
            'attributes': {
                'permission': 'super-user',
                'bibliographic': True
            },
            'relationships': {
                'users': {
                    'data': {
                        'type': 'users',
                        'id': self.user_two._id
                    }
                }
            }
        }
        payload = {'data': [self.payload_two, payload]}
        res = self.app.post_json_api(self.public_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)


class TestNodeContributorBulkUpdate(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorBulkUpdate, self).setUp()
        self.user_three = AuthUserFactory()
        self.user_four = AuthUserFactory()

        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.public_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)

        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

        self.payload_one_public = {
            'id': make_contrib_id(self.public_project._id, self.user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': "admin"
            }
        }

        self.payload_one_private = {
            'id': make_contrib_id(self.private_project._id, self.user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': "admin"
            }
        }

        self.payload_two_public = {
            'id': make_contrib_id(self.public_project._id, self.user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': "write"
            }
        }

        self.payload_two_private = {
            'id': make_contrib_id(self.private_project._id, self.user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': "write"
            }
        }

    def test_bulk_update_contributors_blank_request(self):
        res = self.app.patch_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_update_contributors_dict_instead_of_list(self):
        res = self.app.put_json_api(self.public_url, {'data': self.payload_one_public},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_update_contributors_public_project_one_not_found(self):
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }
        empty_payload = {'data': [invalid_id, self.payload_one_public]}
        res = self.app.put_json_api(self.public_url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

        res = self.app.get(self.public_url)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'] )

    def test_bulk_update_contributors_public_projects_logged_out(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_one_public, self.payload_two_public]},
                                    expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_public_projects_logged_in(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_one_public, self.payload_two_public]},
                                    auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission']],
                           ['admin', 'write'])

    def test_bulk_update_contributors_private_projects_logged_out(self):
        res = self.app.put_json_api(self.private_url, {'data': [self.payload_one_private, self.payload_two_private]},
                                    expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_private_projects_logged_in_contrib(self):
        res = self.app.put_json_api(self.private_url, {'data': [self.payload_one_private, self.payload_two_private]},
                                    auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission']],
                           ['admin', 'write'])

    def test_bulk_update_contributors_private_projects_logged_in_non_contrib(self):
        res = self.app.put_json_api(self.private_url, {'data': [self.payload_one_private, self.payload_two_private]},
                                    auth=self.user_four.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_private_projects_logged_in_read_only_contrib(self):
        res = self.app.put_json_api(self.private_url, {'data': [self.payload_one_private, self.payload_two_private]},
                                    auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_projects_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.public_url, {'data': self.payload_one_public},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_update_contributors_id_not_supplied(self):
        res = self.app.put_json_api(self.public_url, {'data': [{'type': 'contributors', 'attributes': {}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Contributor identifier not provided.")

    def test_bulk_update_contributors_type_not_supplied(self):
        res = self.app.put_json_api(self.public_url, {'data': [{'id': make_contrib_id(self.public_project._id, self.user_two._id), 'attributes': {}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

    def test_bulk_update_contributors_wrong_type(self):
        invalid_type = {
            'id': make_contrib_id(self.public_project._id, self.user_two._id),
            'type': 'Wrong type.',
            'attributes': {}
        }
        res = self.app.put_json_api(self.public_url, {'data': [invalid_type]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_update_contributors_invalid_id_format(self):
        invalid_id = {
            'id': '12345',
            'type': 'contributors',
            'attributes': {}

        }
        res = self.app.put_json_api(self.public_url, {'data': [invalid_id]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Contributor identifier incorrectly formatted.')

    def test_bulk_update_contributors_wrong_id(self):
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }
        res = self.app.put_json_api(self.public_url, {'data': [invalid_id]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

    def test_bulk_update_contributors_limits(self):
        contrib_update_list = {'data': [self.payload_one_public] * 101}
        res = self.app.put_json_api(self.public_url, contrib_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_update_contributors_invalid_permissions(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_two_public, {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors', 'attributes': {'permission': 'super-user'}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '"super-user" is not a valid choice.')

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_invalid_bibliographic(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_two_public, {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors', 'attributes': {'bibliographic': 'true and false'}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '"true and false" is not a valid boolean.')

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_update_contributors_must_have_at_least_one_bibliographic_contributor(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_two_public,
                                                               {'id': make_contrib_id(self.public_project._id, self.user._id), 'type': 'contributors',
                                                                'attributes': {'permission': 'admin', 'bibliographic': False}},
                                                               {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors',
                                                                'attributes': {'bibliographic': False}}
                                                               ]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Must have at least one visible contributor')

    def test_bulk_update_contributors_must_have_at_least_one_admin(self):
        res = self.app.put_json_api(self.public_url, {'data': [self.payload_two_public,
                                                               {'id': make_contrib_id(self.public_project._id, self.user._id), 'type': 'contributors',
                                                                'attributes': {'permission': 'read'}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '{} is the only admin.'.format(self.user.fullname))

class TestNodeContributorBulkPartialUpdate(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorBulkPartialUpdate, self).setUp()
        self.user_three = AuthUserFactory()
        self.user_four = AuthUserFactory()

        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.public_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)

        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

        self.public_payload_one = {
            'id': make_contrib_id(self.public_project._id, self.user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': "admin"
            }
        }

        self.private_payload_one = {
            'id': make_contrib_id(self.private_project._id, self.user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': "admin"
            }
        }

        self.public_payload_two = {
            'id': make_contrib_id(self.public_project._id, self.user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': "write"
            }
        }

        self.private_payload_two = {
            'id': make_contrib_id(self.private_project._id, self.user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': "write"
            }
        }

    def test_bulk_partial_update_contributors_blank_request(self):
        res = self.app.patch_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_partial_update_contributors_public_project_one_not_found(self):
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }

        empty_payload = {'data': [invalid_id, self.public_payload_one]}
        res = self.app.patch_json_api(self.public_url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

        res = self.app.get(self.public_url)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'] )

    def test_bulk_partial_update_contributors_public_projects_logged_out(self):
        res = self.app.patch_json_api(self.public_url,
                                      {'data': [self.public_payload_one, self.public_payload_two]}, bulk=True, expect_errors=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_partial_update_contributors_public_projects_logged_in(self):
        res = self.app.patch_json_api(self.public_url, {'data': [self.public_payload_one, self.public_payload_two]},
                                      auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission']],
                           ['admin', 'write'])

    def test_bulk_partial_update_contributors_private_projects_logged_out(self):
        res = self.app.patch_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                      expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_partial_update_contributors_private_projects_logged_in_contrib(self):
        res = self.app.patch_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                      auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission']],
                           ['admin', 'write'])

    def test_bulk_partial_update_contributors_private_projects_logged_in_non_contrib(self):
        res = self.app.patch_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                      auth=self.user_four.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_partial_update_contributors_private_projects_logged_in_read_only_contrib(self):
        res = self.app.patch_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                      auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])

    def test_bulk_partial_update_contributors_projects_send_dictionary_not_list(self):
        res = self.app.patch_json_api(self.public_url, {'data': self.public_payload_one},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_partial_update_contributors_id_not_supplied(self):
        res = self.app.patch_json_api(self.public_url, {'data': [{'type': 'contributors', 'attributes': {}}]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Contributor identifier not provided.")

    def test_bulk_partial_update_contributors_type_not_supplied(self):
        res = self.app.patch_json_api(self.public_url, {'data': [{'id': make_contrib_id(self.public_project._id, self.user_two._id), 'attributes': {}}]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

    def test_bulk_partial_update_contributors_wrong_type(self):
        invalid_type = {
            'id': make_contrib_id(self.public_project._id, self.user_two._id),
            'type': 'Wrong type.',
            'attributes': {}
        }
        res = self.app.patch_json_api(self.public_url, {'data': [invalid_type]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_partial_update_contributors_wrong_id(self):
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }

        res = self.app.patch_json_api(self.public_url, {'data': [invalid_id]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

    def test_bulk_partial_update_contributors_limits(self):
        contrib_update_list = {'data': [self.public_payload_one] * 101}
        res = self.app.patch_json_api(self.public_url, contrib_update_list, auth=self.user.auth,
                                      expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_partial_update_invalid_permissions(self):
        res = self.app.patch_json_api(self.public_url, {'data': [self.public_payload_two, {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors', 'attributes': {'permission': 'super-user'}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '"super-user" is not a valid choice.')

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])


    def test_bulk_partial_update_invalid_bibliographic(self):
        res = self.app.patch_json_api(self.public_url, {'data': [self.public_payload_two, {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors', 'attributes': {'bibliographic': 'true and false'}}]},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], '"true and false" is not a valid boolean.')

        res = self.app.get(self.public_url, auth=self.user.auth)
        data = res.json['data']
        assert_items_equal([data[0]['attributes']['permission'], data[1]['attributes']['permission'], data[2]['attributes']['permission']],
                           ['admin', 'read', 'read'])


class TestNodeContributorBulkDelete(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorBulkDelete, self).setUp()
        self.user_three = AuthUserFactory()
        self.user_four = AuthUserFactory()

        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.public_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], visible=True, save=True)
        self.private_project.add_contributor(self.user_three, permissions=[permissions.READ], visible=True, save=True)

        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

        self.public_payload_one = {
            'id': make_contrib_id(self.public_project._id, self.user_two._id),
            'type': 'contributors'
        }

        self.private_payload_one = {
            'id': make_contrib_id(self.private_project._id, self.user_two._id),
            'type': 'contributors',
        }

        self.public_payload_two = {
            'id': make_contrib_id(self.public_project._id, self.user_three._id),
            'type': 'contributors'
        }

        self.private_payload_two = {
            'id': make_contrib_id(self.private_project._id, self.user_three._id),
            'type': 'contributors',
        }

    def test_bulk_delete_contributors_blank_request(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_invalid_id_format(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'id': '12345', 'type':'contributors'}]}, auth=self.user.auth,
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Contributor identifier incorrectly formatted.')

    def test_bulk_delete_invalid_id(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'id': '12345-abcde', 'type':'contributors'}]}, auth=self.user.auth,
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to delete.')

    def test_bulk_delete_non_contributor(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'id': make_contrib_id(self.public_project._id, self.user_four._id), 'type':'contributors'}]}, auth=self.user.auth,
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)

    def test_bulk_delete_all_contributors(self):
        res = self.app.delete_json_api(self.public_url, {'data': [self.public_payload_one, self.public_payload_two,
                                                                  {'id': make_contrib_id(self.public_project._id, self.user._id), 'type': 'contributors'}]},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_in(res.json['errors'][0]['detail'], ['Must have at least one registered admin contributor',
                                                    'Must have at least one visible contributor'])
        self.public_project.reload()
        assert_equal(len(self.public_project.contributors), 3)

    def test_bulk_delete_contributors_no_id(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'type': 'contributors'}]},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/id.')

    def test_bulk_delete_contributors_no_type(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'id': make_contrib_id(self.public_project._id, self.user_two._id)}]},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')

    def test_bulk_delete_contributors_invalid_type(self):
        res = self.app.delete_json_api(self.public_url, {'data': [{'type': 'Wrong type', 'id': make_contrib_id(self.public_project._id, self.user_two._id)}]},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.public_url, {'data': {'id': make_contrib_id(self.public_project._id, self.user_two._id), 'type': 'contributors'}},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_contributors_public_project_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = self.app.delete_json_api(self.public_url, {'data': [self.public_payload_one, self.public_payload_two]},
                                           auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_bulk_delete_contributors_public_projects_logged_out(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        res = self.app.delete_json_api(self.public_url, {'data': [self.public_payload_one, self.public_payload_two]},
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_bulk_delete_contributors_private_projects_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = self.app.delete_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                           auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_bulk_delete_contributors_private_projects_logged_out(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        res = self.app.delete_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_bulk_delete_contributors_private_projects_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        res = self.app.delete_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                       auth=self.user_four.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_bulk_delete_contributors_private_projects_logged_in_read_only_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

        res = self.app.delete_json_api(self.private_url, {'data': [self.private_payload_one, self.private_payload_two]},
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_bulk_delete_contributors_all_or_nothing(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
        }

        new_payload = {'data': [self.public_payload_one, invalid_id]}

        res = self.app.delete_json_api(self.public_url, new_payload, auth=self.user.auth,
                                       expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to delete.')

        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)

    def test_bulk_delete_contributors_limits(self):
        new_payload = {'data': [self.public_payload_one] * 101 }
        res = self.app.delete_json_api(self.public_url, new_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_contributors_no_payload(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

