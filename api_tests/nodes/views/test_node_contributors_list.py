# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from website.models import NodeLog

from framework.auth.core import Auth

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    UserFactory
)

from tests.utils import assert_logs
from website.util import permissions

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


class TestNodeContributorList(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorList, self).setUp()
        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    def test_return_public_contributor_list_logged_out(self):
        self.public_project.add_contributor(self.user_two, save=True)

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_public_contributor_list_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.user._id)

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
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_contributor_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


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
        assert_equal(len(res.json['data']), 1)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
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

        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

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
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

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
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

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
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

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

    def test_add_contributor_incorrect_target_type_in_relationships(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'Incorrect!',
                            'id': self.user_two._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

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
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.public_project.reload()
        assert_in(self.user_two, self.public_project.contributors)
        assert_true(self.public_project.get_visible(self.user_two))

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_adds_bibliographic_contributor_public_project_admin(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

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
        assert_equal(res.json['data']['id'], self.user_two._id)
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
        assert_not_in(self.user_three, self.public_project.contributors)

    def test_adds_contributor_public_project_non_contributor(self):
        res = self.app.post_json_api(self.public_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_not_in(self.user_three, self.public_project.contributors)

    def test_adds_contributor_public_project_not_logged_in(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_not_in(self.user_two, self.public_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_contributor_private_project_admin(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

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
        assert_equal(res.json['data']['id'], self.user_two._id)

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
        assert_equal(res.json['data']['id'], self.user_two._id)

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
        assert_equal(res.json['data']['id'], self.user_two._id)

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
        assert_not_in(self.user_two, self.private_project.contributors)

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
        assert_not_in(self.user_three, self.private_project.contributors)

    def test_adds_contributor_private_project_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_not_in(self.user_three, self.private_project.contributors)

    def test_adds_contributor_private_project_not_logged_in(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.private_project.reload()
        assert_not_in(self.user_two, self.private_project.contributors)
