# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from website.models import NodeLog
from website.project.model import Auth
from website.util import permissions

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
from tests.utils import assert_logs, assert_not_logs


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


class TestContributorDetail(NodeCRUDTestCase):
    def setUp(self):
        super(TestContributorDetail, self).setUp()

        self.public_url = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.public_project, self.user._id)
        self.private_url_base = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.private_project._id, '{}')
        self.private_url = self.private_url_base.format(self.user._id)

    def test_get_public_contributor_detail(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.public_project._id, self.user._id))

    def test_get_private_node_contributor_detail_contributor_auth(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], '{}-{}'.format(self.private_project, self.user._id))

    def test_get_private_node_contributor_detail_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_get_private_node_contributor_detail_not_logged_in(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_get_private_node_non_contributor_detail_contributor_auth(self):
        res = self.app.get(self.private_url_base.format(self.user_two._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_private_node_invalid_user_detail_contributor_auth(self):
        res = self.app.get(self.private_url_base.format('invalid'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_unregistered_contributor_detail_show_up_as_name_associated_with_project(self):
        project = ProjectFactory(creator=self.user, public=True)
        project.add_unregistered_contributor('Robert Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        unregistered_contributor = project.contributors[1]
        url = '/{}nodes/{}/contributors/{}/'.format(API_BASE, project._id, unregistered_contributor._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['embeds']['users']['data']['attributes']['full_name'], 'Robert Jackson')
        assert_equal(res.json['data']['attributes'].get('unregistered_contributor'), 'Robert Jackson')

        project_two = ProjectFactory(creator=self.user, public=True)
        project_two.add_unregistered_contributor('Bob Jackson', 'robert@gmail.com', auth=Auth(self.user), save=True)
        url = '/{}nodes/{}/contributors/{}/'.format(API_BASE, project_two._id, unregistered_contributor._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        assert_equal(res.json['data']['embeds']['users']['data']['attributes']['full_name'], 'Robert Jackson')
        assert_equal(res.json['data']['attributes'].get('unregistered_contributor'), 'Bob Jackson')

    def test_detail_includes_index(self):
        res = self.app.get(self.public_url)
        data = res.json['data']
        assert_in('index', data['attributes'].keys())
        assert_equal(data['attributes']['index'], 0)

        other_contributor = AuthUserFactory()
        self.public_project.add_contributor(other_contributor, auth=Auth(self.user), save=True)

        other_contributor_detail = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.public_project, other_contributor._id)
        res = self.app.get(other_contributor_detail)
        assert_equal(res.json['data']['attributes']['index'], 1)


class TestNodeContributorOrdering(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorOrdering, self).setUp()
        self.contributors = [AuthUserFactory() for number in range(1, 10)]
        self.user_one = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user_one)
        for contributor in self.contributors:
            self.project.add_contributor(
                contributor,
                permissions=[permissions.READ, permissions.WRITE],
                visible=True,
                save=True
            )

        self.contributors.insert(0, self.user_one)
        self.base_contributor_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)
        self.url_creator = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_one._id)
        self.contributor_urls = ['/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, contributor._id)
            for contributor in self.contributors]
        self.last_position = len(self.contributors) - 1

    @staticmethod
    def _get_contributor_user_id(contributor):
        return contributor['embeds']['users']['data']['id']

    def test_initial_order(self):
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        found_contributors = False
        for i in range(0, len(self.contributors)):
            assert_equal(self.contributors[i]._id, self._get_contributor_user_id(contributor_list[i]))
            assert_equal(i, contributor_list[i]['attributes']['index'])
            found_contributors = True
        assert_true(found_contributors, "Did not compare any contributors.")

    @assert_logs(NodeLog.CONTRIB_REORDERED, 'project')
    def test_move_top_contributor_down_one_and_also_log(self):
        contributor_to_move = self.contributors[0]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_contributor = self.contributors[1]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 1
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[1]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[0]), former_second_contributor._id)

    def test_move_second_contributor_up_one_to_top(self):
        contributor_to_move = self.contributors[1]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_first_contributor = self.contributors[0]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 0
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[0]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[1]), former_first_contributor._id)

    def test_move_top_contributor_down_to_bottom(self):
        contributor_to_move = self.contributors[0]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_contributor = self.contributors[1]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': self.last_position
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[self.last_position]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[0]), former_second_contributor._id)

    def test_move_bottom_contributor_up_to_top(self):
        contributor_to_move = self.contributors[self.last_position]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_to_last_contributor = self.contributors[self.last_position - 1]

        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 0
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[0]), contributor_to_move)
        assert_equal(
            self._get_contributor_user_id(contributor_list[self.last_position]),
            former_second_to_last_contributor._id
        )

    def test_move_second_to_last_contributor_down_past_bottom(self):
        contributor_to_move = self.contributors[self.last_position - 1]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_last_contributor = self.contributors[self.last_position]

        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': self.last_position + 10
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[self.last_position]), contributor_to_move)
        assert_equal(
            self._get_contributor_user_id(contributor_list[self.last_position - 1]),
            former_last_contributor._id
        )

    def test_move_top_contributor_down_to_second_to_last_position_with_negative_numbers(self):
        contributor_to_move = self.contributors[0]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_contributor = self.contributors[1]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': -1
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=self.user_one.auth)
        assert_equal(res_patch.status_code, 200)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[self.last_position - 1]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[0]), former_second_contributor._id)

    def test_write_contributor_fails_to_move_top_contributor_down_one(self):
        contributor_to_move = self.contributors[0]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_contributor = self.contributors[1]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 1
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, auth=former_second_contributor.auth, expect_errors=True)
        assert_equal(res_patch.status_code, 403)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[0]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[1]), former_second_contributor._id)

    def test_non_authenticated_fails_to_move_top_contributor_down_one(self):
        contributor_to_move = self.contributors[0]._id
        contributor_id = '{}-{}'.format(self.project._id, contributor_to_move)
        former_second_contributor = self.contributors[1]
        url = '{}{}/'.format(self.base_contributor_url, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 1
                }
            }
        }
        res_patch = self.app.patch_json_api(url, data, expect_errors=True)
        assert_equal(res_patch.status_code, 401)
        self.project.reload()
        res = self.app.get('/{}nodes/{}/contributors/'.format(API_BASE, self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        contributor_list = res.json['data']
        assert_equal(self._get_contributor_user_id(contributor_list[0]), contributor_to_move)
        assert_equal(self._get_contributor_user_id(contributor_list[1]), former_second_contributor._id)


class TestNodeContributorUpdate(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorUpdate, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        self.url_creator = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user._id)
        self.url_contributor = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_two._id)

    def test_node_update_invalid_data(self):
        res = self.app.put_json_api(self.url_creator, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.put_json_api(self.url_creator, ["Incorrect data"], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_change_contributor_no_id(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_change_contributor_correct_id(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_change_contributor_incorrect_id(self):
        data = {
            'data': {
                'id': '12345',
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_change_contributor_no_type(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_change_contributor_incorrect_type(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'Wrong type.',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)


    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -3)
    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -2)
    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_change_contributor_permissions(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.ADMIN)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE, permissions.ADMIN])

        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])

        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.READ)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ])

    @assert_logs(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, 'project', -2)
    @assert_logs(NodeLog.MADE_CONTRIBUTOR_VISIBLE, 'project')
    def test_change_contributor_bibliographic(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['bibliographic'], False)

        self.project.reload()
        assert_false(self.project.get_visible(self.user_two))

        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['bibliographic'], True)

        self.project.reload()
        assert_true(self.project.get_visible(self.user_two))

    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -2)
    @assert_logs(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, 'project')
    def test_change_contributor_permission_and_bibliographic(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.READ)
        assert_equal(attributes['bibliographic'], False)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ])
        assert_false(self.project.get_visible(self.user_two))

    @assert_not_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_not_change_contributor(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': None,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)
        assert_equal(attributes['bibliographic'], True)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    def test_invalid_change_inputs_contributor(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user_two._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': 'invalid',
                    'bibliographic': 'invalid'
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_change_admin_self_with_other_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        contrib_id = '{}-{}'.format(self.project._id, self.user._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user), [permissions.READ, permissions.WRITE])

    def test_change_admin_self_without_other_admin(self):
        contrib_id = '{}-{}'.format(self.project._id, self.user._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user), [permissions.READ, permissions.WRITE, permissions.ADMIN])

    def test_remove_all_bibliographic_statuses_contributors(self):
        self.project.set_visible(self.user_two, False, save=True)
        contrib_id = '{}-{}'.format(self.project._id, self.user._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_true(self.project.get_visible(self.user))

    def test_change_contributor_non_admin_auth(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    def test_change_contributor_not_logged_in(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))


class TestNodeContributorPartialUpdate(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorPartialUpdate, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        self.url_creator = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user._id)
        self.url_contributor = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_two._id)

    def test_patch_bibliographic_only(self):
        creator_id = '{}-{}'.format(self.project._id, self.user._id)
        data = {
            'data': {
                'id': creator_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False,
                }
            }
        }
        res = self.app.patch_json_api(self.url_creator, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(self.project.get_permissions(self.user), [permissions.READ, permissions.WRITE, permissions.ADMIN])
        assert_false(self.project.get_visible(self.user))

    def test_patch_permission_only(self):
        user_three = AuthUserFactory()
        self.project.add_contributor(user_three, permissions=[permissions.READ, permissions.WRITE], visible=False, save=True)
        url_contributor = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, user_three._id)
        contributor_id = '{}-{}'.format(self.project._id, user_three._id)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                }
            }
        }
        res = self.app.patch_json_api(url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(self.project.get_permissions(user_three), [permissions.READ])
        assert_false(self.project.get_visible(user_three))


class TestNodeContributorDelete(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorDelete, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        self.url_user = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user._id)
        self.url_user_two = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_two._id)
        self.url_user_three = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_three._id)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_contributor_admin(self):
        res = self.app.delete(self.url_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_two, self.project.contributors)

    def test_remove_contributor_non_admin_is_forbidden(self):
        self.project.add_contributor(self.user_three, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        res = self.app.delete(self.url_user_three, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_in(self.user_three, self.project.contributors)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_self_non_admin(self):
        self.project.add_contributor(self.user_three, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        res = self.app.delete(self.url_user_three, auth=self.user_three.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_three, self.project.contributors)

    def test_remove_contributor_non_contributor(self):
        res = self.app.delete(self.url_user_two, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_in(self.user_two, self.project.contributors)

    def test_remove_contributor_not_logged_in(self):
        res = self.app.delete(self.url_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_in(self.user_two, self.project.contributors)

    def test_remove_non_contributor_admin(self):
        assert_not_in(self.user_three, self.project.contributors)
        res = self.app.delete(self.url_user_three, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        self.project.reload()
        assert_not_in(self.user_three, self.project.contributors)

    def test_remove_non_existing_user_admin(self):
        url_user_fake = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, 'fake')
        res = self.app.delete(url_user_fake, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_self_contributor_not_unique_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        res = self.app.delete(self.url_user, auth=self.user.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user, self.project.contributors)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_can_remove_self_as_contributor_not_unique_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        res = self.app.delete(self.url_user_two, auth=self.user_two.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_two, self.project.contributors)

    def test_remove_self_contributor_unique_admin(self):
        res = self.app.delete(self.url_user, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_in(self.user, self.project.contributors)

    def test_can_not_remove_only_bibliographic_contributor(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        self.project.set_visible(self.user_two, False, save=True)
        res = self.app.delete(self.url_user, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_in(self.user, self.project.contributors)
