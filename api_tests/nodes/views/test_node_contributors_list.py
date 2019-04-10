# -*- coding: utf-8 -*-
from datetime import datetime
import mock
import pytest
import random

from api.base.settings.defaults import API_BASE
from api.nodes.serializers import NodeContributorsCreateSerializer
from framework.auth.core import Auth
from osf.models import NodeLog
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
    UnconfirmedUserFactory,
    UserFactory,

)
from osf.utils import permissions
from rest_framework import exceptions
from tests.base import capture_signals, fake
from tests.utils import assert_latest_log, assert_items_equal
from website.project.signals import contributor_added, contributor_removed
from api_tests.utils import disconnected_from_listeners

@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class NodeCRUDTestCase:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def title(self):
        return 'Cool Project'

    @pytest.fixture()
    def title_new(self):
        return 'Super Cool Project'

    @pytest.fixture()
    def description(self):
        return 'A Properly Cool Project'

    @pytest.fixture()
    def description_new(self):
        return 'An even cooler project'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def category_new(self):
        return 'project'

    @pytest.fixture()
    def project_public(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )

    @pytest.fixture()
    def project_private(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/'.format(API_BASE, project_private._id)

    @pytest.fixture()
    def url_fake(self):
        return '/{}nodes/{}/'.format(API_BASE, '12345')

    @pytest.fixture()
    def make_contrib_id(self):
        def contrib_id(node_id, user_id):
            return '{}-{}'.format(node_id, user_id)
        return contrib_id


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestNodeContributorList(NodeCRUDTestCase):

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    def test_concatenated_id(self, app, user, project_public, url_public):
        res = app.get(url_public)
        assert res.status_code == 200

        assert res.json['data'][0]['id'].split('-')[0] == project_public._id
        assert res.json['data'][0]['id'] == '{}-{}'.format(
            project_public._id, user._id)

    def test_permissions_work_with_many_users(
            self, app, user, project_private, url_private):
        users = {
            'admin': [user._id],
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

            project_private.add_contributor(user, permissions=perms)
            users[perm].append(user._id)

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        for user in data:
            api_perm = user['attributes']['permission']
            user_id = user['id'].split('-')[1]
            assert user_id in users[api_perm], 'Permissions incorrect for {}. Should not have {} permission.'.format(
                user_id, api_perm)

    def test_return(
            self, app, user, user_two, project_public,
            url_public, url_private, make_contrib_id):

        #   test_return_public_contributor_list_logged_in
        res = app.get(url_public, auth=user_two.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == make_contrib_id(
            project_public._id, user._id)

    #   test_return_private_contributor_list_logged_out
        res = app.get(url_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_contributor_list_logged_in_non_contributor
        res = app.get(url_private, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_return_public_contributor_list_logged_out(
            self, app, user, user_two, project_public, url_public, make_contrib_id):
        project_public.add_contributor(user_two, save=True)

        res = app.get(url_public)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == make_contrib_id(
            project_public._id, user._id)
        assert res.json['data'][1]['id'] == make_contrib_id(
            project_public._id, user_two._id)

    def test_return_private_contributor_list_logged_in_contributor(
            self, app, user, user_two, project_private, url_private, make_contrib_id):
        project_private.add_contributor(user_two)
        project_private.save()

        res = app.get(url_private, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == make_contrib_id(
            project_private._id, user._id)
        assert res.json['data'][1]['id'] == make_contrib_id(
            project_private._id, user_two._id)

    def test_filtering_on_obsolete_fields(self, app, user, url_public):
        # regression test for changes in filter fields
        url_fullname = '{}?filter[fullname]=foo'.format(url_public)
        res = app.get(url_fullname, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'fullname\' is not a valid field for this endpoint.'

        # middle_name is now middle_names
        url_middle_name = '{}?filter[middle_name]=foo'.format(url_public)
        res = app.get(url_middle_name, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'middle_name\' is not a valid field for this endpoint.'

    def test_disabled_contributors_contain_names_under_meta(
            self, app, user, user_two, project_public, url_public, make_contrib_id):
        project_public.add_contributor(user_two, save=True)

        user_two.is_disabled = True
        user_two.save()

        res = app.get(url_public)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == make_contrib_id(
            project_public._id, user._id)
        assert res.json['data'][1]['id'] == make_contrib_id(
            project_public._id, user_two._id)
        assert res.json['data'][1]['embeds']['users']['errors'][0]['meta']['full_name'] == user_two.fullname
        assert res.json['data'][1]['embeds']['users']['errors'][0]['detail'] == 'The requested user is no longer available.'

    def test_total_bibliographic_contributor_count_returned_in_metadata(
            self, app, user_two, project_public, url_public):
        non_bibliographic_user = UserFactory()
        project_public.add_contributor(
            non_bibliographic_user,
            visible=False,
            auth=Auth(project_public.creator))
        project_public.save()
        res = app.get(url_public, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['links']['meta']['total_bibliographic'] == len(
            project_public.visible_contributor_ids)

    def test_unregistered_contributor_field_is_null_if_account_claimed(
            self, app, user):
        project = ProjectFactory(creator=user, is_public=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes'].get(
            'unregistered_contributor') is None

    def test_unregistered_contributors_show_up_as_name_associated_with_project(
            self, app, user):
        project = ProjectFactory(creator=user, is_public=True)
        project.add_unregistered_contributor(
            'Robert Jackson',
            'robert@gmail.com',
            auth=Auth(user), save=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][1]['embeds']['users']['data']['attributes']['full_name'] == 'Robert Jackson'
        assert res.json['data'][1]['attributes'].get(
            'unregistered_contributor') == 'Robert Jackson'

        project_two = ProjectFactory(creator=user, is_public=True)
        project_two.add_unregistered_contributor(
            'Bob Jackson', 'robert@gmail.com', auth=Auth(user), save=True)
        url = '/{}nodes/{}/contributors/'.format(API_BASE, project_two._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 2

        assert res.json['data'][1]['embeds']['users']['data']['attributes']['full_name'] == 'Robert Jackson'
        assert res.json['data'][1]['attributes'].get(
            'unregistered_contributor') == 'Bob Jackson'

    def test_contributors_order_is_the_same_over_multiple_requests(
            self, app, user, project_public, url_public):
        project_public.add_unregistered_contributor(
            'Robert Jackson',
            'robert@gmail.com',
            auth=Auth(user), save=True
        )

        for i in range(0, 10):
            new_user = AuthUserFactory()
            if i % 2 == 0:
                visible = True
            else:
                visible = False
            project_public.add_contributor(
                new_user,
                visible=visible,
                auth=Auth(project_public.creator),
                save=True
            )
        req_one = app.get(
            '{}?page=2'.format(url_public),
            auth=Auth(project_public.creator))
        req_two = app.get(
            '{}?page=2'.format(url_public),
            auth=Auth(project_public.creator))
        id_one = [item['id'] for item in req_one.json['data']]
        id_two = [item['id'] for item in req_two.json['data']]
        for a, b in zip(id_one, id_two):
            assert a == b


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestNodeContributorAdd(NodeCRUDTestCase):

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/?send_email=false'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/?send_email=false'.format(
            API_BASE, project_public._id)

    @pytest.fixture()
    def data_user_two(self, user_two):
        return {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id,
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def data_user_three(self, user_three):
        return {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True,
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_three._id,
                        }
                    }
                }
            }
        }

    def test_add_contributors_errors(
            self, app, user, user_two, user_three, url_public):

        #   test_add_node_contributors_relationships_is_a_list
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': [{'contributor_id': user_three._id}]
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_add_contributor_no_relationships
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A user ID or full name must be provided to add a contributor.'

    #   test_add_contributor_empty_relationships
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {}
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A user ID or full name must be provided to add a contributor.'

    #   test_add_contributor_no_user_key_in_relationships
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'id': user_two._id,
                    'type': 'users'
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_add_contributor_no_data_in_relationships
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'id': user_two._id
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'

    #   test_add_contributor_no_target_type_in_relationships
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

    #   test_add_contributor_no_target_id_in_relationships
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
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A user ID or full name must be provided to add a contributor.'

    #   test_add_contributor_incorrect_target_id_in_relationships
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
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_add_contributor_no_type
        data = {
            'data': {
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_add_contributor_incorrect_type
        data = {
            'data': {
                'type': 'Incorrect type',
                'attributes': {
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'id': user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    def test_contributor_create_invalid_data(
            self, app, user_three, url_public):
        res = app.post_json_api(
            url_public,
            'Incorrect data',
            auth=user_three.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

        res = app.post_json_api(
            url_public,
            ['Incorrect data'],
            auth=user_three.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_add_contributor_dont_expose_email(
            self, app, user, user_two, project_public, data_user_two, url_public):

        res = app.post_json_api(
            url_public,
            data_user_two,
            auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes'].get('email') is None

    def test_add_contributor_is_visible_by_default(
            self, app, user, user_two, project_public,
            data_user_two, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
            del data_user_two['data']['attributes']['bibliographic']
            res = app.post_json_api(
                url_public,
                data_user_two,
                auth=user.auth,
                expect_errors=True)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_public._id, user_two._id)

            project_public.reload()
            assert user_two in project_public.contributors
            assert project_public.get_visible(user_two)

    def test_adds_bibliographic_contributor_public_project_admin(
            self, app, user, user_two, project_public, data_user_two, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
            res = app.post_json_api(url_public, data_user_two, auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_public._id, user_two._id)

            project_public.reload()
            assert user_two in project_public.contributors

    def test_adds_non_bibliographic_contributor_private_project_admin(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
            data = {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': False
                    },
                    'relationships': {
                        'users': {
                            'data': {
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(
                url_private, data, auth=user.auth,
                expect_errors=True)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_private._id, user_two._id)
            assert res.json['data']['attributes']['bibliographic'] is False

            project_private.reload()
            assert user_two in project_private.contributors
            assert not project_private.get_visible(user_two)

    def test_adds_contributor_public_project_non_admin(
            self, app, user, user_two, user_three,
            project_public, data_user_three, url_public):
        project_public.add_contributor(
            user_two,
            permissions=[
                permissions.READ,
                permissions.WRITE],
            auth=Auth(user),
            save=True)
        res = app.post_json_api(url_public, data_user_three,
                                auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        project_public.reload()
        assert user_three not in project_public.contributors.all()

    def test_adds_contributor_public_project_non_contributor(
            self, app, user_two, user_three, project_public, data_user_three, url_public):
        res = app.post_json_api(url_public, data_user_three,
                                auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert user_three not in project_public.contributors.all()

    def test_adds_contributor_public_project_not_logged_in(
            self, app, user_two, project_public, data_user_two, url_public):
        res = app.post_json_api(url_public, data_user_two, expect_errors=True)
        assert res.status_code == 401
        assert user_two not in project_public.contributors.all()

    def test_adds_contributor_private_project_admin(
            self, app, user, user_two, project_private,
            data_user_two, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
            res = app.post_json_api(url_private, data_user_two, auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_private._id, user_two._id)

            project_private.reload()
            assert user_two in project_private.contributors

    def test_adds_contributor_without_bibliographic_private_project_admin(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
            data = {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                    },
                    'relationships': {
                        'users': {
                            'data': {
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(
                url_private, data, auth=user.auth,
                expect_errors=True)
            assert res.status_code == 201

            project_private.reload()
            assert user_two in project_private.contributors

    def test_adds_admin_contributor_private_project_admin(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
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
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(url_private, data, auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_private._id, user_two._id)

            project_private.reload()
            assert user_two in project_private.contributors
            assert project_private.get_permissions(user_two) == [
                permissions.READ, permissions.WRITE, permissions.ADMIN]

    def test_adds_write_contributor_private_project_admin(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
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
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(url_private, data, auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_private._id, user_two._id)

            project_private.reload()
            assert user_two in project_private.contributors
            assert project_private.get_permissions(
                user_two) == [permissions.READ, permissions.WRITE]

    def test_adds_read_contributor_private_project_admin(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
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
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(url_private, data, auth=user.auth)
            assert res.status_code == 201
            assert res.json['data']['id'] == '{}-{}'.format(
                project_private._id, user_two._id)

            project_private.reload()
            assert user_two in project_private.contributors
            assert project_private.get_permissions(user_two) == [
                permissions.READ]

    def test_adds_invalid_permission_contributor_private_project_admin(
            self, app, user, user_two, project_private, url_private):
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
                            'id': user_two._id,
                            'type': 'users'
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_private, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

        project_private.reload()
        assert user_two not in project_private.contributors.all()

    def test_adds_none_permission_contributor_private_project_admin_uses_default_permissions(
            self, app, user, user_two, project_private, url_private):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_private):
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
                                'id': user_two._id,
                                'type': 'users'
                            }
                        }
                    }
                }
            }
            res = app.post_json_api(url_private, data, auth=user.auth)
            assert res.status_code == 201

            project_private.reload()
            assert user_two in project_private.contributors
            for permission in permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS:
                assert project_private.has_permission(user_two, permission)

    def test_adds_already_existing_contributor_private_project_admin(
            self, app, user, user_two, project_private, data_user_two, url_private):
        project_private.add_contributor(user_two, auth=Auth(user), save=True)
        project_private.reload()

        res = app.post_json_api(url_private, data_user_two,
                                auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_adds_non_existing_user_private_project_admin(
            self, app, user, project_private, url_private):
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
        res = app.post_json_api(
            url_private, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

        project_private.reload()
        assert len(project_private.contributors) == 1

    def test_adds_contributor_private_project_non_admin(
            self, app, user, user_two, user_three,
            project_private, data_user_three, url_private):
        project_private.add_contributor(
            user_two,
            permissions=[
                permissions.READ,
                permissions.WRITE],
            auth=Auth(user))
        res = app.post_json_api(
            url_private, data_user_three,
            auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        project_private.reload()
        assert user_three not in project_private.contributors.all()

    def test_adds_contributor_private_project_non_contributor(
            self, app, user_two, user_three, project_private, data_user_three, url_private):
        res = app.post_json_api(url_private, data_user_three,
                                auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        project_private.reload()
        assert user_three not in project_private.contributors.all()

    def test_adds_contributor_private_project_not_logged_in(
            self, app, user_two, project_private, data_user_two, url_private):
        res = app.post_json_api(url_private, data_user_two, expect_errors=True)
        assert res.status_code == 401

        project_private.reload()
        assert user_two not in project_private.contributors.all()

    def test_add_unregistered_contributor_with_fullname(
            self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
            payload = {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'full_name': 'John Doe',
                    }
                }
            }
            res = app.post_json_api(url_public, payload, auth=user.auth)
            project_public.reload()
            assert res.status_code == 201
            assert res.json['data']['attributes']['unregistered_contributor'] == 'John Doe'
            assert res.json['data']['attributes'].get('email') is None
            assert res.json['data']['embeds']['users']['data']['id'] in project_public.contributors.values_list(
                'guids___id', flat=True)

    def test_add_contributor_with_fullname_and_email_unregistered_user(
            self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
            payload = {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'full_name': 'John Doe',
                        'email': 'john@doe.com'
                    }
                }
            }
            res = app.post_json_api(url_public, payload, auth=user.auth)
            project_public.reload()
            assert res.status_code == 201
            assert res.json['data']['attributes']['unregistered_contributor'] == 'John Doe'
            assert res.json['data']['attributes'].get('email') is None
            assert res.json['data']['attributes']['bibliographic'] is True
            assert res.json['data']['attributes']['permission'] == permissions.WRITE
            assert res.json['data']['embeds']['users']['data']['id'] in project_public.contributors.values_list(
                'guids___id', flat=True)

    def test_add_contributor_with_fullname_and_email_unregistered_user_set_attributes(
            self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
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
            res = app.post_json_api(url_public, payload, auth=user.auth)
            project_public.reload()
            assert res.status_code == 201
            assert res.json['data']['attributes']['unregistered_contributor'] == 'John Doe'
            assert res.json['data']['attributes'].get('email') is None
            assert res.json['data']['attributes']['bibliographic'] is False
            assert res.json['data']['attributes']['permission'] == permissions.READ
            assert res.json['data']['embeds']['users']['data']['id'] in project_public.contributors.values_list(
                'guids___id', flat=True)

    def test_add_contributor_with_fullname_and_email_registered_user(
            self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.CONTRIB_ADDED, project_public):
            user_contrib = UserFactory()
            payload = {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'full_name': user_contrib.fullname,
                        'email': user_contrib.username
                    }
                }
            }
            res = app.post_json_api(url_public, payload, auth=user.auth)
            project_public.reload()
            assert res.status_code == 201
            assert res.json['data']['attributes']['unregistered_contributor'] is None
            assert res.json['data']['attributes'].get('email') is None
            assert res.json['data']['embeds']['users']['data']['id'] in project_public.contributors.values_list(
                'guids___id', flat=True)

    def test_add_unregistered_contributor_already_contributor(
            self, app, user, project_public, url_public):
        name, email = fake.name(), fake_email()
        project_public.add_unregistered_contributor(
            auth=Auth(user), fullname=name, email=email)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Doesn\'t Matter',
                    'email': email
                }
            }
        }
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        project_public.reload()
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '{} is already a contributor.'.format(
            name)

    def test_add_contributor_user_is_deactivated_registered_payload(
            self, app, user, url_public):
        user_contrib = UserFactory()
        user_contrib.date_disabled = datetime.utcnow()
        user_contrib.save()
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {},
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_contrib._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Deactivated users cannot be added as contributors.'

    def test_add_contributor_user_is_deactivated_unregistered_payload(
            self, app, user, url_public):
        user_contrib = UserFactory()
        user_contrib.date_disabled = datetime.utcnow()
        user_contrib.save()
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': user_contrib.fullname,
                    'email': user_contrib.username
                },
            }
        }
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Deactivated users cannot be added as contributors.'

    def test_add_contributor_index_returned(
            self, app, user, data_user_two,
            data_user_three, url_public):
        res = app.post_json_api(url_public, data_user_two, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['index'] == 1

        res = app.post_json_api(url_public, data_user_three, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['index'] == 2

    def test_add_contributor_set_index_out_of_range(
            self, app, user, user_two, project_public, url_public):
        user_contrib_one = UserFactory()
        project_public.add_contributor(user_contrib_one, save=True)
        user_contrib_two = UserFactory()
        project_public.add_contributor(user_contrib_two, save=True)
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
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '4 is not a valid contributor index for node with id {}'.format(
            project_public._id)

    def test_add_contributor_set_index_first(
            self, app, user, user_two, project_public, url_public):
        user_contrib_one = UserFactory()
        project_public.add_contributor(user_contrib_one, save=True)
        user_contrib_two = UserFactory()
        project_public.add_contributor(user_contrib_two, save=True)
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
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(url_public, payload, auth=user.auth)
        project_public.reload()
        assert res.status_code == 201
        contributor_obj = project_public.contributor_set.get(user=user_two)
        index = list(
            project_public.get_contributor_order()
        ).index(contributor_obj.pk)
        assert index == 0

    def test_add_contributor_set_index_last(
            self, app, user, user_two, project_public, url_public):
        user_contrib_one = UserFactory()
        project_public.add_contributor(user_contrib_one, save=True)
        user_contrib_two = UserFactory()
        project_public.add_contributor(user_contrib_two, save=True)
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
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(url_public, payload, auth=user.auth)
        project_public.reload()
        assert res.status_code == 201
        contributor_obj = project_public.contributor_set.get(user=user_two)
        index = list(
            project_public.get_contributor_order()
        ).index(contributor_obj.pk)
        assert index == 3

    def test_add_inactive_merged_user_as_contributor(
            self, app, user, url_public):
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

        res = app.post_json_api(url_public, payload, auth=user.auth)
        assert res.status_code == 201
        contributor_added = res.json['data']['embeds']['users']['data']['id']
        assert contributor_added == primary_user._id

    def test_add_unconfirmed_user_by_guid(
            self, app, user, project_public, url_public):
        unconfirmed_user = UnconfirmedUserFactory()
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {},
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': unconfirmed_user._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        # if adding unregistered contrib by guid, fullname must be supplied
        assert (
            res.json['errors'][0]['detail'] ==
            'Cannot add unconfirmed user {} to resource {}. You need to provide a full_name.'
            .format(unconfirmed_user._id, project_public._id))

        payload['data']['attributes']['full_name'] = 'Susan B. Anthony'
        res = app.post_json_api(
            url_public, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 201
        assert res.json['data']['attributes']['unregistered_contributor'] == 'Susan B. Anthony'


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestNodeContributorCreateValidation(NodeCRUDTestCase):

    @pytest.fixture()
    def validate_data(self):
        return NodeContributorsCreateSerializer.validate_data

    def test_add_contributor_validation(self, project_public, validate_data):

        #   test_add_contributor_validation_user_id
        validate_data(
            NodeContributorsCreateSerializer(),
            project_public,
            user_id='abcde')

    #   test_add_contributor_validation_user_id_fullname
        validate_data(
            NodeContributorsCreateSerializer(),
            project_public,
            user_id='abcde',
            full_name='Kanye')

    #   test_add_contributor_validation_user_id_email
        with pytest.raises(exceptions.ValidationError):
            validate_data(
                NodeContributorsCreateSerializer(),
                project_public,
                user_id='abcde',
                email='kanye@west.com')

    #   test_add_contributor_validation_user_id_fullname_email
        with pytest.raises(exceptions.ValidationError):
            validate_data(
                NodeContributorsCreateSerializer(),
                project_public,
                user_id='abcde',
                full_name='Kanye',
                email='kanye@west.com')

    #   test_add_contributor_validation_fullname
        validate_data(
            NodeContributorsCreateSerializer(),
            project_public,
            full_name='Kanye')

    #   test_add_contributor_validation_email
        with pytest.raises(exceptions.ValidationError):
            validate_data(
                NodeContributorsCreateSerializer(),
                project_public,
                email='kanye@west.com')

    #   test_add_contributor_validation_fullname_email
        validate_data(
            NodeContributorsCreateSerializer(),
            project_public,
            full_name='Kanye',
            email='kanye@west.com')


@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_enqueue_task
class TestNodeContributorCreateEmail(NodeCRUDTestCase):

    @pytest.fixture()
    def url_project_contribs(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_no_email_if_false(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=false'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_sends_email(
            self, mock_mail, app, user, user_two,
            url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id
                        }
                    }
                }
            }
        }

        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1

    @mock.patch('website.project.signals.contributor_added.send')
    def test_add_contributor_signal_if_default(
            self, mock_send, app, user, user_two, url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        args, kwargs = mock_send.call_args
        assert res.status_code == 201
        assert 'default' == kwargs['email_template']

    def test_add_contributor_signal_preprint_email_disallowed(
            self, app, user, user_two, url_project_contribs):
        url = '{}?send_email=preprint'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'preprint is not a valid email preference.'

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_sends_email(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1

    @mock.patch('website.project.signals.unreg_contributor_added.send')
    def test_add_unregistered_contributor_signal_if_default(
            self, mock_send, app, user, url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        args, kwargs = mock_send.call_args
        assert res.status_code == 201
        assert 'default' == kwargs['email_template']

    def test_add_unregistered_contributor_signal_preprint_email_disallowed(
            self, app, user, url_project_contribs):
        url = '{}?send_email=preprint'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'preprint is not a valid email preference.'

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_invalid_send_email_param(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=true'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'true is not a valid email preference.'
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_without_email_no_email(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                }
            }
        }

        with capture_signals() as mock_signal:
            res = app.post_json_api(url, payload, auth=user.auth)
        assert contributor_added in mock_signal.signals_sent()
        assert res.status_code == 201
        assert mock_mail.call_count == 0


@pytest.mark.django_db
class TestNodeContributorBulkCreate(NodeCRUDTestCase):

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/?send_email=false'.format(
            API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/?send_email=false'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def payload_one(self, user_two):
        return {
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': 'admin'
            },
            'relationships': {
                'users': {
                    'data': {
                        'id': user_two._id,
                        'type': 'users'
                    }
                }
            }
        }

    @pytest.fixture()
    def payload_two(self, user_three):
        return {
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'read'
            },
            'relationships': {
                'users': {
                    'data': {
                        'id': user_three._id,
                        'type': 'users'
                    }
                }
            }
        }

    def test_node_contributor_bulk_create_contributor_exists(
            self, app, user, user_two, project_public,
            payload_one, payload_two, url_public):
        project_public.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        res = app.post_json_api(
            url_public,
            {'data': [payload_two, payload_one]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert 'is already a contributor' in res.json['errors'][0]['detail']

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 2

    def test_node_contributor_bulk_create_errors(
            self, app, user, user_two, project_private,
            payload_one, payload_two, url_public, url_private):

        #   test_bulk_create_contributors_blank_request
        res = app.post_json_api(
            url_public, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_node_contributor_bulk_create_logged_out_public_project
        res = app.post_json_api(
            url_public,
            {'data': [payload_one, payload_two]},
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_node_contributor_bulk_create_logged_out_private_project
        res = app.post_json_api(
            url_private,
            {'data': [payload_one, payload_two]},
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_node_contributor_bulk_create_logged_in_non_contrib_private_project
        res = app.post_json_api(url_private, {'data': [payload_one, payload_two]},
                                auth=user_two.auth, expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_node_contributor_bulk_create_logged_in_read_only_contrib_private_project
        project_private.add_contributor(
            user_two, permissions=[permissions.READ], save=True)
        res = app.post_json_api(
            url_private,
            {'data': [payload_two]},
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1

    def test_node_contributor_bulk_create_logged_in_public_project_project(
            self, app, user, payload_one, payload_two, url_public):
        res = app.post_json_api(
            url_public,
            {'data': [payload_one, payload_two]},
            auth=user.auth, bulk=True)
        assert res.status_code == 201
        assert_items_equal([res.json['data'][0]['attributes']['bibliographic'],
                            res.json['data'][1]['attributes']['bibliographic']], [True, False])
        assert_items_equal([res.json['data'][0]['attributes']['permission'],
                            res.json['data'][1]['attributes']['permission']], ['admin', 'read'])
        assert res.content_type == 'application/vnd.api+json'

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

    def test_node_contributor_bulk_create_logged_in_contrib_private_project(
            self, app, user, payload_one, payload_two, url_private):
        res = app.post_json_api(url_private, {'data': [payload_one, payload_two]},
                                auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 201
        assert len(res.json['data']) == 2
        assert_items_equal([res.json['data'][0]['attributes']['bibliographic'],
                            res.json['data'][1]['attributes']['bibliographic']], [True, False])
        assert_items_equal([res.json['data'][0]['attributes']['permission'],
                            res.json['data'][1]['attributes']['permission']], ['admin', 'read'])
        assert res.content_type == 'application/vnd.api+json'

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

    def test_node_contributor_bulk_create_payload_errors(
            self, app, user, user_two, payload_one, payload_two, url_public):

        #   test_node_contributor_bulk_create_all_or_nothing
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
        res = app.post_json_api(
            url_public,
            {'data': [payload_one, invalid_id_payload]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 404

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_node_contributor_bulk_create_limits
        node_contrib_create_list = {'data': [payload_one] * 101}
        res = app.post_json_api(url_public, node_contrib_create_list,
                                auth=user.auth, expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_node_contributor_ugly_payload
        payload = 'sdf;jlasfd'
        res = app.post_json_api(
            url_public, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_node_contributor_bulk_create_invalid_permissions_all_or_nothing
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
                        'id': user_two._id
                    }
                }
            }
        }
        payload = {'data': [payload_two, payload]}
        res = app.post_json_api(
            url_public, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1


@pytest.mark.django_db
class TestNodeContributorBulkUpdate(NodeCRUDTestCase):

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_four(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        project_public.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True)
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three,
            title, description, category):
        project_private = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def payload_public_one(self, user_two, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': 'admin'
            }
        }

    @pytest.fixture()
    def payload_private_one(self, user_two, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': 'admin'
            }
        }

    @pytest.fixture()
    def payload_public_two(self, user_three, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'write'
            }
        }

    @pytest.fixture()
    def payload_private_two(
            self, user_three, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'write'
            }
        }

    def test_bulk_update_contributors_errors(
            self, app, user, user_two, user_four, project_public,
            payload_public_one, payload_public_two,
            payload_private_one, payload_private_two,
            url_public, url_private, make_contrib_id):

        #   test_bulk_update_contributors_blank_request
        res = app.patch_json_api(
            url_public, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_update_contributors_dict_instead_of_list
        res = app.put_json_api(
            url_public,
            {'data': payload_public_one},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_update_contributors_public_project_one_not_found
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }
        empty_payload = {'data': [invalid_id, payload_public_one]}
        res = app.put_json_api(
            url_public, empty_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        res = app.get(url_public)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_update_contributors_public_projects_logged_out
        res = app.put_json_api(
            url_public,
            {
                'data': [payload_public_one,
                         payload_public_two]
            },
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_update_contributors_private_projects_logged_out
        res = app.put_json_api(
            url_private,
            {
                'data': [payload_private_one,
                         payload_private_two]
            },
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    #   test_bulk_update_contributors_private_projects_logged_in_non_contrib
        res = app.put_json_api(
            url_private,
            {
                'data': [payload_private_one,
                         payload_private_two]
            },
            auth=user_four.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    #   test_bulk_update_contributors_private_projects_logged_in_read_only_contrib
        res = app.put_json_api(
            url_private,
            {
                'data': [payload_private_one,
                         payload_private_two]
            },
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_update_contributors_projects_send_dictionary_not_list
        res = app.put_json_api(
            url_public,
            {'data': payload_public_one},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_update_contributors_id_not_supplied
        res = app.put_json_api(
            url_public,
            {'data': [{
                'type': 'contributors',
                'attributes': {}
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Contributor identifier not provided.'

    #   test_bulk_update_contributors_type_not_supplied
        res = app.put_json_api(
            url_public,
            {'data': [{
                'id': make_contrib_id(
                    project_public._id, user_two._id
                ),
                'attributes': {}
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

    #   test_bulk_update_contributors_wrong_type
        invalid_type = {
            'id': make_contrib_id(project_public._id, user_two._id),
            'type': 'Wrong type.',
            'attributes': {}
        }
        res = app.put_json_api(url_public, {'data': [invalid_type]},
                               auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 409

    #   test_bulk_update_contributors_invalid_id_format
        invalid_id = {
            'id': '12345',
            'type': 'contributors',
            'attributes': {}

        }
        res = app.put_json_api(url_public, {'data': [invalid_id]},
                               auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Contributor identifier incorrectly formatted.'

    #   test_bulk_update_contributors_wrong_id
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }
        res = app.put_json_api(
            url_public, {'data': [invalid_id]},
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

    #   test_bulk_update_contributors_limits
        contrib_update_list = {'data': [payload_public_one] * 101}
        res = app.put_json_api(
            url_public, contrib_update_list,
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_update_contributors_invalid_permissions
        res = app.put_json_api(
            url_public,
            {
                'data': [
                    payload_public_two, {
                        'id': make_contrib_id(
                            project_public._id, user_two._id
                        ),
                        'type': 'contributors',
                        'attributes': {
                            'permission': 'super-user'}
                    }
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"super-user" is not a valid choice.'

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_update_contributors_invalid_bibliographic
        res = app.put_json_api(
            url_public,
            {
                'data': [
                    payload_public_two, {
                        'id': make_contrib_id(
                            project_public._id, user_two._id
                        ),
                        'type': 'contributors',
                        'attributes': {
                            'bibliographic': 'true and false'
                        }
                    }
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"true and false" is not a valid boolean.'

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_update_contributors_must_have_at_least_one_bibliographic_contributor
        res = app.put_json_api(
            url_public,
            {
                'data': [
                    payload_public_two, {
                        'id': make_contrib_id(
                            project_public._id, user._id
                        ),
                        'type': 'contributors',
                        'attributes': {
                            'permission': 'admin',
                            'bibliographic': False
                        }
                    }, {
                        'id': make_contrib_id(
                            project_public._id, user_two._id
                        ),
                        'type': 'contributors',
                        'attributes': {
                            'bibliographic': False
                        }
                    }
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Must have at least one visible contributor'

    #   test_bulk_update_contributors_must_have_at_least_one_admin
        res = app.put_json_api(
            url_public,
            {'data': [
                payload_public_two, {
                    'id': make_contrib_id(
                        project_public._id, user._id
                    ),
                    'type': 'contributors',
                    'attributes': {
                            'permission': 'read'
                    }
                }
            ]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '{} is the only admin.'.format(
            user.fullname)

    def test_bulk_update_contributors_public_projects_logged_in(
            self, app, user, payload_public_one, payload_public_two, url_public):
        res = app.put_json_api(
            url_public,
            {'data': [payload_public_one, payload_public_two]},
            auth=user.auth, bulk=True
        )
        assert res.status_code == 200
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission']],
            ['admin', 'write']
        )

    def test_bulk_update_contributors_private_projects_logged_in_contrib(
            self, app, user, payload_private_one, payload_private_two, url_private):
        res = app.put_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            auth=user.auth, bulk=True
        )
        assert res.status_code == 200
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission']],
            ['admin', 'write']
        )


@pytest.mark.django_db
class TestNodeContributorBulkPartialUpdate(NodeCRUDTestCase):

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_four(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True
        )
        project_public.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True
        )
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three, title,
            description, category):
        project_private = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def payload_public_one(self, user_two, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': 'admin'
            }
        }

    @pytest.fixture()
    def payload_public_two(self, user_three, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'write'
            }
        }

    @pytest.fixture()
    def payload_private_one(self, user_two, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_two._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': True,
                'permission': 'admin'
            }
        }

    @pytest.fixture()
    def payload_private_two(
            self, user_three, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_three._id),
            'type': 'contributors',
            'attributes': {
                'bibliographic': False,
                'permission': 'write'
            }
        }

    def test_bulk_partial_update_errors(
            self, app, user, user_two, user_four,
            project_public, payload_public_one,
            payload_public_two, payload_private_one,
            payload_private_two, url_public,
            url_private, make_contrib_id):

        #   test_bulk_partial_update_contributors_blank_request
        res = app.patch_json_api(
            url_public, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_partial_update_contributors_public_project_one_not_found
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }

        empty_payload = {'data': [invalid_id, payload_public_one]}
        res = app.patch_json_api(
            url_public, empty_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        res = app.get(url_public)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_partial_update_contributors_public_projects_logged_out
        res = app.patch_json_api(
            url_public,
            {'data': [payload_public_one, payload_public_two]},
            bulk=True, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_partial_update_contributors_private_projects_logged_out
        res = app.patch_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            expect_errors=True, bulk=True
        )
        assert res.status_code == 401

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    #   test_bulk_partial_update_contributors_private_projects_logged_in_non_contrib
        res = app.patch_json_api(
            url_private,
            {'data': [payload_private_one,
                      payload_private_two]},
            auth=user_four.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read']
        )

    #   test_bulk_partial_update_contributors_private_projects_logged_in_read_only_contrib
        res = app.patch_json_api(
            url_private,
            {'data': [payload_private_one,
                      payload_private_two]},
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    #   test_bulk_partial_update_contributors_projects_send_dictionary_not_list
        res = app.patch_json_api(
            url_public,
            {'data': payload_public_one},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_partial_update_contributors_id_not_supplied
        res = app.patch_json_api(
            url_public,
            {'data': [{
                'type': 'contributors',
                'attributes': {}
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Contributor identifier not provided.'

    #   test_bulk_partial_update_contributors_type_not_supplied
        res = app.patch_json_api(
            url_public,
            {'data': [{
                'id': make_contrib_id(
                    project_public._id,
                    user_two._id
                ),
                'attributes': {}
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

    #   test_bulk_partial_update_contributors_wrong_type
        invalid_type = {
            'id': make_contrib_id(project_public._id, user_two._id),
            'type': 'Wrong type.',
            'attributes': {}
        }
        res = app.patch_json_api(
            url_public, {'data': [invalid_type]},
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 409

    #   test_bulk_partial_update_contributors_wrong_id
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
            'attributes': {}
        }

        res = app.patch_json_api(
            url_public, {'data': [invalid_id]},
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

    #   test_bulk_partial_update_contributors_limits
        contrib_update_list = {'data': [payload_public_one] * 101}
        res = app.patch_json_api(
            url_public, contrib_update_list,
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_partial_update_invalid_permissions
        res = app.patch_json_api(
            url_public,
            {
                'data': [
                    payload_public_two, {
                        'id': make_contrib_id(
                            project_public._id,
                            user_two._id
                        ),
                        'type': 'contributors',
                        'attributes': {'permission': 'super-user'}
                    }]
            },
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"super-user" is not a valid choice.'

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    #   test_bulk_partial_update_invalid_bibliographic
        res = app.patch_json_api(
            url_public,
            {
                'data': [
                    payload_public_two, {
                        'id': make_contrib_id(
                            project_public._id, user_two._id),
                        'type': 'contributors',
                        'attributes': {'bibliographic': 'true and false'}
                    }
                ]
            },
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"true and false" is not a valid boolean.'

        res = app.get(url_public, auth=user.auth)
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission'],
             data[2]['attributes']['permission']],
            ['admin', 'read', 'read'])

    def test_bulk_partial_update_contributors_public_projects_logged_in(
            self, app, user, payload_public_one, payload_public_two, url_public):
        res = app.patch_json_api(
            url_public,
            {'data': [payload_public_one, payload_public_two]},
            auth=user.auth, bulk=True)
        assert res.status_code == 200
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission']],
            ['admin', 'write'])

    def test_bulk_partial_update_contributors_private_projects_logged_in_contrib(
            self, app, user, payload_private_one, payload_private_two, url_private):
        res = app.patch_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            auth=user.auth, bulk=True)
        assert res.status_code == 200
        data = res.json['data']
        assert_items_equal(
            [data[0]['attributes']['permission'],
             data[1]['attributes']['permission']],
            ['admin', 'write'])


class TestNodeContributorBulkDelete(NodeCRUDTestCase):

    @pytest.fixture()
    def user_three(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_four(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        project_public.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True)
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three, title,
            description, category):
        project_private = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=[permissions.READ],
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=[permissions.READ],
            visible=True, save=True)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/contributors/'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def payload_public_one(self, user_two, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_two._id),
            'type': 'contributors'
        }

    @pytest.fixture()
    def payload_public_two(self, user_three, project_public, make_contrib_id):
        return {
            'id': make_contrib_id(project_public._id, user_three._id),
            'type': 'contributors'
        }

    @pytest.fixture()
    def payload_private_one(self, user_two, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_two._id),
            'type': 'contributors',
        }

    @pytest.fixture()
    def payload_private_two(
            self, user_three, project_private, make_contrib_id):
        return {
            'id': make_contrib_id(project_private._id, user_three._id),
            'type': 'contributors',
        }

    def test_bulk_delete_contributors_errors(
            self, app, user, user_two, user_four,
            project_public, payload_public_one,
            payload_public_two, payload_private_one,
            payload_private_two, url_public,
            url_private, make_contrib_id):

        #   test_bulk_delete_contributors_blank_request
        res = app.delete_json_api(
            url_public, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_delete_invalid_id_format
        res = app.delete_json_api(
            url_public,
            {'data': [{
                'id': '12345',
                'type': 'contributors'
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Contributor identifier incorrectly formatted.'

    #   test_bulk_delete_invalid_id
        res = app.delete_json_api(
            url_public,
            {'data': [{
                'id': '12345-abcde',
                'type': 'contributors'
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to delete.'

    #   test_bulk_delete_non_contributor
        res = app.delete_json_api(
            url_public,
            {'data': [{
                'id': make_contrib_id(
                    project_public._id, user_four._id
                ),
                'type': 'contributors'
            }]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 404

    #   test_bulk_delete_all_contributors
        res = app.delete_json_api(
            url_public,
            {'data': [
                payload_public_one,
                payload_public_two,
                {
                    'id': make_contrib_id(
                        project_public._id, user._id
                    ),
                    'type': 'contributors'
                }
            ]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] in [
            'Must have at least one registered admin contributor',
            'Must have at least one visible contributor']
        project_public.reload()
        assert len(project_public.contributors) == 3

    #   test_bulk_delete_contributors_no_id
        res = app.delete_json_api(
            url_public,
            {'data': [{'type': 'contributors'}]},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/id.'

    #   test_bulk_delete_contributors_no_type
        res = app.delete_json_api(
            url_public,
            {'data': [{'id': make_contrib_id(
                project_public._id, user_two._id
            )}]},
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

    #   test_bulk_delete_contributors_invalid_type
        res = app.delete_json_api(
            url_public,
            {'data': [{
                'type': 'Wrong type',
                'id': make_contrib_id(
                    project_public._id, user_two._id)
            }]},
            auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 409

    #   test_bulk_delete_dict_inside_data
        res = app.delete_json_api(
            url_public,
            {
                'data': {
                    'id': make_contrib_id(
                        project_public._id,
                        user_two._id),
                    'type': 'contributors'}},
            auth=user.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_delete_contributors_public_projects_logged_out
        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

        res = app.delete_json_api(
            url_public,
            {'data': [payload_public_one, payload_public_two]},
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

    #   test_bulk_delete_contributors_private_projects_logged_out
        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

        res = app.delete_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            expect_errors=True, bulk=True)
        assert res.status_code == 401

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

    #   test_bulk_delete_contributors_private_projects_logged_in_non_contributor
        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

        res = app.delete_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            auth=user_four.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

    #   test_bulk_delete_contributors_private_projects_logged_in_read_only_contributor
        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

        res = app.delete_json_api(
            url_private,
            {'data': [payload_private_one, payload_private_two]},
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

    #   test_bulk_delete_contributors_all_or_nothing
        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3
        invalid_id = {
            'id': '12345-abcde',
            'type': 'contributors',
        }

        new_payload = {'data': [payload_public_one, invalid_id]}

        res = app.delete_json_api(
            url_public, new_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to delete.'

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

    #   test_bulk_delete_contributors_limits
        new_payload = {'data': [payload_public_one] * 101}
        res = app.delete_json_api(
            url_public, new_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_delete_contributors_no_payload
        res = app.delete_json_api(
            url_public, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    def test_bulk_delete_contributors_public_project_logged_in(
            self, app, user, payload_public_one, payload_public_two, url_public):
        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 3

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete_json_api(
                url_public,
                {'data': [payload_public_one, payload_public_two]},
                auth=user.auth, bulk=True)
        assert res.status_code == 204

        res = app.get(url_public, auth=user.auth)
        assert len(res.json['data']) == 1

    def test_bulk_delete_contributors_private_projects_logged_in_contributor(
            self, app, user, payload_private_one, payload_private_two, url_private):
        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 3

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete_json_api(
                url_private,
                {'data': [payload_private_one, payload_private_two]},
                auth=user.auth, bulk=True)
        assert res.status_code == 204

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == 1


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestNodeContributorFiltering:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    def test_filtering(self, app, user, project):

        #   test_filtering_full_name_field
        url = '/{}nodes/{}/contributors/?filter[full_name]=Freddie'.format(
            API_BASE, project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'full_name\' is not a valid field for this endpoint.'

    #   test_filtering_permission_field
        url = '/{}nodes/{}/contributors/?filter[permission]=admin'.format(
            API_BASE, project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes'].get('permission') == 'admin'

    #   test_filtering_node_with_only_bibliographic_contributors
        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)
        # no filter
        res = app.get(base_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes'].get('bibliographic', None)

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filtering_on_invalid_field
        url = '/{}nodes/{}/contributors/?filter[invalid]=foo'.format(
            API_BASE, project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'invalid\' is not a valid field for this endpoint.'

    def test_filtering_node_with_non_bibliographic_contributor(
            self, app, user, project):
        non_bibliographic_contrib = UserFactory()
        project.add_contributor(non_bibliographic_contrib, visible=False)
        project.save()

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, project._id)

        # no filter
        res = app.get(base_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes'].get('bibliographic', None)

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert not res.json['data'][0]['attributes'].get('bibliographic', None)
