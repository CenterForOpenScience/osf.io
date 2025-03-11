import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NodeLog
from osf_tests.factories import (
    ProjectFactory,
    OSFGroupFactory,
    AuthUserFactory,
)
from rest_framework import exceptions
from tests.utils import assert_latest_log, assert_latest_log_not
from osf.utils import permissions

@pytest.mark.django_db
class TestNodeContributorUpdate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user, contrib):
        project = ProjectFactory(creator=user)
        project.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True
        )
        return project

    @pytest.fixture()
    def url_creator(self, user, project):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user._id}/'

    @pytest.fixture()
    def url_contrib(self, project, contrib):
        return f'/{API_BASE}nodes/{project._id}/contributors/{contrib._id}/'

    def test_change_contributor_no_id(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    def test_change_contributor_incorrect_id(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': '12345',
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_change_contributor_no_type(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': f'{project._id}-{contrib._id}',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    def test_change_contributor_wrong_type(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': contrib._id,
                    'type': 'Wrong type.',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    def test_invalid_change_inputs_contributor(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': f'{project._id}-{contrib._id}',
                    'type': 'contributors',
                    'attributes': {
                        'permission': 'invalid',
                        'bibliographic': 'invalid'
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]
        assert project.get_visible(contrib)

    def test_change_contributor_not_logged_in(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': contrib._id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                        'bibliographic': False
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 401
        assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]
        assert project.get_visible(contrib)

    def test_change_contributor_non_admin_auth(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': contrib._id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                        'bibliographic': False
                    }
                }
            },
            auth=contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]
        assert project.get_visible(contrib)

    def test_change_contributor_non_admin_osf_group_member_auth(self, app, user, contrib, project, url_contrib):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        project.add_osf_group(group, permissions.WRITE)
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': contrib._id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                        'bibliographic': False
                    }
                }
            },
            auth=group_mem.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]
        assert project.get_visible(contrib)

    def test_change_admin_self_without_other_admin(self, app, user, project, url_creator):
        res = app.put_json_api(
            url_creator,
            {
                'data': {
                    'id': f'{project._id}-{user._id}',
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.WRITE,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert project.get_permissions(user) == [permissions.READ, permissions.WRITE, permissions.ADMIN]

    def test_node_update_invalid_data(self, app, user, url_creator):
        res = app.put_json_api(
            url_creator,
            'Incorrect data',
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_node_update_invalid_data_list(self, app, user, url_creator):

        res = app.put_json_api(
            url_creator,
            ['Incorrect data'],
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_change_contributor_correct_id(self, app, user, contrib, project, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': f'{project._id}-{contrib._id}',
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 200

    def test_change_contributor_admin_osf_group_permissions(self, app, user, contrib, project, url_contrib):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        project.add_osf_group(group, permissions.ADMIN)
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': f'{project._id}-{contrib._id}',
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            },
            auth=group_mem.auth,
            expect_errors=True
        )
        assert res.status_code == 200

    def test_remove_all_bibliographic_statuses_contributors(self, app, user, contrib, project, url_creator):
        project.set_visible(contrib, False, save=True)
        res = app.put_json_api(
            url_creator,
            {
                'data': {
                    'id': f'{project._id}-{user._id}',
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': False
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert project.get_visible(user)

    def test_change_contributor_permissions(self, app, user, contrib, project, url_contrib):
        with assert_latest_log(NodeLog.PERMISSIONS_UPDATED, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': permissions.ADMIN,
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.ADMIN
            assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE, permissions.ADMIN]

        with assert_latest_log(NodeLog.PERMISSIONS_UPDATED, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': permissions.WRITE,
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE
            assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]

        with assert_latest_log(NodeLog.PERMISSIONS_UPDATED, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': permissions.READ,
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.READ
            assert project.get_permissions(contrib) == [permissions.READ]

    def test_change_contributor_bibliographic(self, app, user, contrib, project, url_contrib):
        with assert_latest_log(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'bibliographic': False
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert not attributes['bibliographic']

            project.reload()
            assert not project.get_visible(contrib)

        with assert_latest_log(NodeLog.MADE_CONTRIBUTOR_VISIBLE, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['bibliographic']
            assert project.get_visible(contrib)

    def test_change_contributor_permission_and_bibliographic(self, app, user, contrib, project, url_contrib):
        with assert_latest_log(NodeLog.PERMISSIONS_UPDATED, project, 1), assert_latest_log(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': permissions.READ,
                            'bibliographic': False
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.READ
            assert not attributes['bibliographic']
            assert project.get_permissions(contrib) == [permissions.READ]
            assert not project.get_visible(contrib)

    def test_not_change_contributor(self, app, user, contrib, project, url_contrib):
        with assert_latest_log_not(NodeLog.PERMISSIONS_UPDATED, project):
            res = app.put_json_api(
                url_contrib,
                {
                    'data': {
                        'id': f'{project._id}-{contrib._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': None,
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE
            assert attributes['bibliographic']
            assert project.get_permissions(contrib) == [permissions.READ, permissions.WRITE]
            assert project.get_visible(contrib)

    def test_change_admin_self_with_other_admin(self, app, user, contrib, project, url_creator):
        with assert_latest_log(NodeLog.PERMISSIONS_UPDATED, project):
            project.add_permission(contrib, permissions.ADMIN, save=True)
            res = app.put_json_api(
                url_creator,
                {
                    'data': {
                        'id': f'{project._id}-{user._id}',
                        'type': 'contributors',
                        'attributes': {
                            'permission': permissions.WRITE,
                            'bibliographic': True
                        }
                    }
                },
                auth=user.auth
            )
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE
            assert project.get_permissions(user) == [permissions.READ, permissions.WRITE]
