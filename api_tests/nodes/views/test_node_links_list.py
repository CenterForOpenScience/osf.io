import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import NodeLog
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    OSFGroupFactory,
    AuthUserFactory
)
from osf.utils.permissions import WRITE, READ
from rest_framework import exceptions
from tests.utils import assert_latest_log


def node_url_for(n_id):
    return '/{}nodes/{}/'.format(API_BASE, n_id)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeLinksList:

    @pytest.fixture()
    def public_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_pointer_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_project(self, user, private_pointer_project):
        private_project = ProjectFactory(is_public=False, creator=user)
        private_project.add_pointer(private_pointer_project, auth=Auth(user))
        return private_project

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_pointer_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_project(self, user, public_pointer_project):
        public_project = ProjectFactory(is_public=True, creator=user)
        public_project.add_pointer(public_pointer_project, auth=Auth(user))
        return public_project

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, public_project._id)

    def test_non_mutational_node_links_list_tests(
            self, app, user, public_non_contrib, public_pointer_project, private_project,
            private_pointer_project, public_url, private_url):

        #   test_return_embedded_public_node_pointers_logged_out
        res = app.get(public_url)
        res_json = res.json['data']
        assert len(res_json) == 1
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == public_pointer_project._id

    #   test_return_embedded_public_node_pointers_logged_in
        res = app.get(public_url, auth=public_non_contrib.auth)
        res_json = res.json['data']
        assert len(res_json) == 1
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == public_pointer_project._id

    #   test_return_private_node_pointers_logged_out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_node_pointers_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res_json) == 1
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == private_pointer_project._id

    #   test_return_private_node_pointers_logged_in_non_contributor
        res = app.get(
            private_url,
            auth=public_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_osf_group_member_read_can_view
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, READ)
        res = app.get(
            private_url,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 200

    #   test_node_links_bad_version
        url = '{}?version=2.1'.format(public_url)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This feature is deprecated as of version 2.1'

    def test_deleted_links_not_returned(
            self, app, public_url, public_pointer_project):
        res = app.get(public_url, expect_errors=True)
        res_json = res.json['data']
        original_length = len(res_json)

        public_pointer_project.is_deleted = True
        public_pointer_project.save()

        res = app.get(public_url)
        res_json = res.json['data']
        assert len(res_json) == original_length - 1


@pytest.mark.django_db
class TestNodeLinkCreate:

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_pointer_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_url(self, user, private_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, public_project._id)

    @pytest.fixture()
    def fake_url(self):
        return '/{}nodes/{}/node_links/'.format(API_BASE, 'rheis')

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two_project(self, user_two):
        return ProjectFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def user_two_url(self, user_two_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, user_two_project._id)

    @pytest.fixture()
    def make_payload(self):

        # creates a fake payload by default

        def payload(id='rheis'):
            return {
                'data': {
                    'type': 'node_links',
                    'relationships': {
                        'nodes': {
                            'data': {
                                'id': id,
                                'type': 'nodes'
                            }
                        }
                    }
                }
            }

        return payload

    def test_add_node_link(
            self, app, user, public_pointer_project, public_url):

        #   test_add_node_link_relationships_is_a_list
        data = {
            'data': {
                'type': 'node_links',
                'relationships': [{
                    'target_node_id': public_pointer_project._id
                }]
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_add_node_link_no_relationships
        data = {
            'data': {
                'type': 'node_links',
                'attributes': {
                    'id': public_pointer_project._id
                }
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'

    #   test_add_node_links_empty_relationships
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {}
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'

    #   test_add_node_links_no_nodes_key_in_relationships
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'data': {
                        'id': public_pointer_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_add_node_links_no_data_in_relationships
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'id': public_pointer_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'

    #   test_add_node_links_no_target_type_in_relationships
        data = {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': public_pointer_project._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

    #   test_add_node_links_no_target_id_in_relationships
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
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_add_node_links_incorrect_target_id_in_relationships
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
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    #   test_add_node_links_incorrect_target_type_in_relationships
        data = {
            'data': {
                'type': 'nodes',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'Incorrect!',
                            'id': public_pointer_project._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            public_url, data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    def test_create_node_link_invalid_data(self, app, user, public_url):
        res = app.post_json_api(
            public_url, 'Incorrect data',
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_creates_node_link_target_not_nested(
            self, app, user_two, private_pointer_project, public_url):
        payload = {
            'data': {
                'type': 'node_links',
                'id': private_pointer_project._id
            }
        }
        res = app.post_json_api(
            public_url, payload,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'

    def test_creates_public_node_pointer_logged_out(
            self, app, public_url, public_pointer_project, make_payload):
        public_payload = make_payload(id=public_pointer_project._id)
        res = app.post_json_api(public_url, public_payload, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_creates_public_node_pointer_logged_in(
            self, app, user, user_two, public_project,
            public_pointer_project, public_url, make_payload):
        public_payload = make_payload(id=public_pointer_project._id)
        with assert_latest_log(NodeLog.POINTER_CREATED, public_project):
            res = app.post_json_api(
                public_url, public_payload,
                auth=user_two.auth, expect_errors=True)
            assert res.status_code == 403
            assert 'detail' in res.json['errors'][0]

            group_mem = AuthUserFactory()
            group = OSFGroupFactory(creator=group_mem)
            public_project.add_osf_group(group, READ)
            res = app.post_json_api(
                public_url, public_payload,
                auth=group_mem.auth, expect_errors=True)
            assert res.status_code == 403

            res = app.post_json_api(public_url, public_payload, auth=user.auth)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json['embeds']['target_node']['data']['id']
            assert embedded == public_pointer_project._id

    def test_creates_private_node_pointer_logged_out(
            self, app, private_pointer_project, private_url, make_payload):
        private_payload = make_payload(id=private_pointer_project._id)
        res = app.post_json_api(
            private_url, private_payload,
            expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_creates_private_node_pointer_group_member(
            self, app, private_project, private_pointer_project, private_url, make_payload):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, WRITE)
        private_payload = make_payload(id=private_pointer_project._id)
        res = app.post_json_api(
            private_url, private_payload, auth=group_mem.auth)
        assert res.status_code == 201

    def test_creates_private_node_pointer_logged_in_contributor(
            self, app, user, private_pointer_project, private_url, make_payload):
        private_payload = make_payload(id=private_pointer_project._id)
        res = app.post_json_api(private_url, private_payload, auth=user.auth)
        assert res.status_code == 201
        res_json = res.json['data']
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == private_pointer_project._id
        assert res.content_type == 'application/vnd.api+json'

    def test_creates_private_node_pointer_logged_in_non_contributor(
            self, app, user_two, private_pointer_project, private_url, make_payload):
        private_payload = make_payload(id=private_pointer_project._id)
        res = app.post_json_api(
            private_url, private_payload,
            auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_non_contributing_node_to_contributing_node(
            self, app, user_two, user_two_project, private_url, make_payload):
        user_two_payload = make_payload(id=user_two_project._id)
        res = app.post_json_api(
            private_url, user_two_payload,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_contributing_node_to_non_contributing_node(
            self, app, user, user_two_project, private_project,
            private_url, make_payload):
        with assert_latest_log(NodeLog.POINTER_CREATED, private_project):
            user_two_payload = make_payload(id=user_two_project._id)
            res = app.post_json_api(
                private_url, user_two_payload, auth=user.auth)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json['embeds']['target_node']['data']['id']
            assert embedded == user_two_project._id

    def test_create_pointer_non_contributing_node_to_fake_node(
            self, app, user_two, private_url, make_payload):
        fake_payload = make_payload()
        res = app.post_json_api(
            private_url, fake_payload,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_create_pointer_contributing_node_to_fake_node(
            self, app, user, private_url, make_payload):
        fake_payload = make_payload()
        res = app.post_json_api(
            private_url, fake_payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'detail' in res.json['errors'][0]

    def test_create_fake_node_pointing_to_contributing_node(
            self, app, user, user_two, private_pointer_project, fake_url, make_payload):
        private_payload = make_payload(id=private_pointer_project._id)
        res = app.post_json_api(
            fake_url, private_payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        res = app.post_json_api(
            fake_url, private_payload,
            auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_to_itself(
            self, app, user, public_project,
            public_url, make_payload):
        point_to_itself_payload = make_payload(id=public_project._id)
        res = app.post_json_api(
            public_url,
            point_to_itself_payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_create_node_pointer_errors(
            self, app, user, user_two, public_project,
            user_two_project, public_pointer_project,
            public_url, private_url, make_payload):

        #   test_create_node_pointer_to_itself_unauthorized
        point_to_itself_payload = make_payload(id=public_project._id)
        res = app.post_json_api(
            public_url, point_to_itself_payload,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_create_node_pointer_already_connected
        with assert_latest_log(NodeLog.POINTER_CREATED, public_project):
            public_payload = make_payload(id=public_pointer_project._id)
            res = app.post_json_api(public_url, public_payload, auth=user.auth)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json['embeds']['target_node']['data']['id']
            assert embedded == public_pointer_project._id

            res = app.post_json_api(
                public_url, public_payload,
                auth=user.auth, expect_errors=True)
            assert res.status_code == 400
            assert 'detail' in res.json['errors'][0]

    #   test_create_node_pointer_no_type
        payload = {
            'data': {
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_create_node_pointer_incorrect_type
        payload = {
            'data': {
                'type': 'Wrong type.',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "node_links", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

    def test_cannot_add_link_to_registration(
            self, app, user, public_pointer_project, make_payload):
        registration = RegistrationFactory(creator=user)
        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        payload = make_payload(id=public_pointer_project._id)

        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestNodeLinksBulkCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_pointer_project_one(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_pointer_project_two(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer_project_one(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer_project_two(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, public_project._id)

    @pytest.fixture()
    def user_two_project(self, user_two):
        return ProjectFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def user_two_url(self, user_two_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, user_two_project._id)

    @pytest.fixture()
    def private_payload(
            self, private_pointer_project_one, private_pointer_project_two):
        return {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': private_pointer_project_one._id,
                            'type': 'nodes'
                        }
                    }
                }
            },
                {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': private_pointer_project_two._id,
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

    @pytest.fixture()
    def public_payload(
            self, public_pointer_project_one, public_pointer_project_two):
        return {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': public_pointer_project_one._id,
                            'type': 'nodes'
                        }
                    }
                }
            },
                {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': public_pointer_project_two._id,
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

    @pytest.fixture()
    def user_two_payload(self, user_two_project):
        return {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': user_two_project._id,
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

    def test_bulk_create_errors(
            self, app, user, user_two, public_project, user_two_project,
            private_pointer_project_one, public_url, private_url,
            public_payload, private_payload, user_two_payload):

        #   test_bulk_create_node_links_blank_request
        res = app.post_json_api(
            public_url, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_creates_pointers_limits
        payload = {'data': [public_payload['data'][0]] * 101}
        res = app.post_json_api(
            public_url, payload,
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        res = app.get(public_url)
        assert res.json['data'] == []

    #   test_bulk_creates_project_target_not_nested
        payload = {'data': [{'type': 'node_links',
                             'target_node_id': private_pointer_project_one._id}]}
        res = app.post_json_api(
            public_url, payload,
            auth=user_two.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'

    #   test_bulk_creates_public_node_pointers_logged_out
        res = app.post_json_api(
            public_url, public_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        res = app.get(public_url)
        assert res.json['data'] == []

    #   test_bulk_creates_public_node_pointer_logged_in_non_contrib
        res = app.post_json_api(
            public_url, public_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403

    #   test_bulk_creates_private_node_pointers_logged_out
        res = app.post_json_api(
            private_url, private_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        res = app.get(private_url, auth=user.auth)
        assert res.json['data'] == []

    #   test_bulk_creates_private_node_pointers_logged_in_non_contributor
        res = app.post_json_api(
            private_url, private_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        res = app.get(private_url, auth=user.auth)
        assert res.json['data'] == []

    #   test_bulk_creates_node_pointers_non_contributing_node_to_contributing_node
        res = app.post_json_api(
            private_url, user_two_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_creates_pointers_non_contributing_node_to_fake_node
        fake_payload = {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': 'rheis',
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

        res = app.post_json_api(
            private_url, fake_payload,
            auth=user_two.auth,
            expect_errors=True,
            bulk=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_creates_pointers_contributing_node_to_fake_node
        fake_payload = {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': 'rheis',
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

        res = app.post_json_api(
            private_url, fake_payload,
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_creates_fake_nodes_pointing_to_contributing_node
        fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'rheis')

        res = app.post_json_api(
            fake_url, private_payload,
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        res = app.post_json_api(
            fake_url, private_payload,
            auth=user_two.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_creates_node_pointer_to_itself_unauthorized
        point_to_itself_payload = {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': public_project._id
                        }
                    }
                }
            }]
        }

        res = app.post_json_api(
            public_url, point_to_itself_payload,
            bulk=True, auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_creates_node_pointer_no_type
        payload = {
            'data': [{
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': user_two_project._id
                        }
                    }
                }
            }]
        }
        res = app.post_json_api(
            private_url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'

    #   test_bulk_creates_node_pointer_incorrect_type
        payload = {
            'data': [{
                'type': 'Wrong type.',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': user_two_project._id
                        }
                    }
                }
            }]
        }
        res = app.post_json_api(
            private_url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "node_links", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

    def test_bulk_creates_public_node_pointer_logged_in_contrib(
            self, app, user, public_project,
            public_pointer_project_one,
            public_pointer_project_two,
            public_url, public_payload):
        with assert_latest_log(NodeLog.POINTER_CREATED, public_project):
            res = app.post_json_api(
                public_url, public_payload,
                auth=user.auth, bulk=True)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json[0]['embeds']['target_node']['data']['id']
            assert embedded == public_pointer_project_one._id

            embedded = res_json[1]['embeds']['target_node']['data']['id']
            assert embedded == public_pointer_project_two._id

    def test_bulk_creates_private_node_pointer_logged_in_contributor(
            self, app, user, private_project, private_payload,
            private_pointer_project_one, private_pointer_project_two,
            private_url):
        with assert_latest_log(NodeLog.POINTER_CREATED, private_project):
            res = app.post_json_api(
                private_url, private_payload,
                auth=user.auth, bulk=True)
            assert res.status_code == 201
            res_json = res.json['data']
            embedded = res_json[0]['embeds']['target_node']['data']['id']
            assert embedded == private_pointer_project_one._id

            embedded = res_json[1]['embeds']['target_node']['data']['id']
            assert embedded == private_pointer_project_two._id
            assert res.content_type == 'application/vnd.api+json'

    def test_bulk_creates_node_pointers_contributing_node_to_non_contributing_node(
            self, app, user, private_project, user_two_project,
            user_two_payload, private_url):
        with assert_latest_log(NodeLog.POINTER_CREATED, private_project):
            res = app.post_json_api(
                private_url, user_two_payload,
                auth=user.auth, bulk=True)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json[0]['embeds']['target_node']['data']['id']
            assert embedded == user_two_project._id

            res = app.get(private_url, auth=user.auth)
            res_json = res.json['data']
            embedded = res_json[0]['embeds']['target_node']['data']['id']
            assert embedded == user_two_project._id

    def test_bulk_creates_node_pointer_to_itself(
            self, app, user, public_project, public_url):
        point_to_itself_payload = {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': public_project._id
                        }
                    }
                }
            }]
        }

        res = app.post_json_api(
            public_url, point_to_itself_payload,
            auth=user.auth, bulk=True, expect_errors=True)
        assert res.status_code == 400

    def test_bulk_creates_node_pointer_already_connected(
            self, app, user, public_project,
            public_pointer_project_one,
            public_pointer_project_two,
            public_url, public_payload):
        with assert_latest_log(NodeLog.POINTER_CREATED, public_project):
            res = app.post_json_api(
                public_url, public_payload,
                auth=user.auth, bulk=True)
            assert res.status_code == 201
            assert res.content_type == 'application/vnd.api+json'
            res_json = res.json['data']
            embedded = res_json[0]['embeds']['target_node']['data']['id']
            assert embedded == public_pointer_project_one._id

            embedded_two = res_json[1]['embeds']['target_node']['data']['id']
            assert embedded_two == public_pointer_project_two._id

            res = app.post_json_api(
                public_url, public_payload,
                auth=user.auth,
                expect_errors=True, bulk=True)
            assert res.status_code == 400
            assert 'Target Node \'{}\' already pointed to by \'{}\'.'.format(
                public_pointer_project_one._id,
                public_project._id
            ) in res.json['errors'][0]['detail']

    def test_bulk_cannot_add_link_to_registration(
            self, app, user, public_pointer_project_one):
        registration = RegistrationFactory(creator=user)

        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        payload = {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': public_pointer_project_one._id
                        }
                    }
                }
            }]
        }
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestBulkDeleteNodeLinks:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user, is_public=False)

    @pytest.fixture()
    def private_project_pointer_project_one(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def private_project_pointer_project_two(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def private_pointer_one(
            self, user, private_project,
            private_project_pointer_project_one):
        return private_project.add_pointer(
            private_project_pointer_project_one, auth=Auth(user), save=True)

    @pytest.fixture()
    def private_pointer_two(
            self, user, private_project,
            private_project_pointer_project_two):
        return private_project.add_pointer(
            private_project_pointer_project_two, auth=Auth(user), save=True)

    @pytest.fixture()
    def private_payload(self, private_pointer_one, private_pointer_two):
        return {
            'data': [
                {'type': 'node_links', 'id': private_pointer_one._id},
                {'type': 'node_links', 'id': private_pointer_two._id}
            ]
        }

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_project_pointer_project_one(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_project_pointer_project_two(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_pointer_one(
            self, user, public_project,
            public_project_pointer_project_one):
        return public_project.add_pointer(
            public_project_pointer_project_one, auth=Auth(user), save=True)

    @pytest.fixture()
    def public_pointer_two(
            self, user, public_project,
            public_project_pointer_project_two):
        return public_project.add_pointer(
            public_project_pointer_project_two, auth=Auth(user), save=True)

    @pytest.fixture()
    def public_payload(self, public_pointer_one, public_pointer_two):
        return {
            'data': [
                {'type': 'node_links', 'id': public_pointer_one._id},
                {'type': 'node_links', 'id': public_pointer_two._id}
            ]
        }

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/node_links/'.format(API_BASE, public_project._id)

    def test_bulk_delete_errors(
            self, app, user, non_contrib, public_project,
            public_pointer_one, public_pointer_two,
            public_project_pointer_project_one,
            public_project_pointer_project_two,
            public_url, private_url, public_payload,
            private_payload):

        #   test_bulk_delete_node_links_blank_request
        res = app.delete_json_api(
            public_url, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    #   test_bulk_delete_pointer_limits
        res = app.delete_json_api(
            public_url,
            {'data': [public_payload['data'][0]] * 101},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    #   test_bulk_delete_dict_inside_data
        res = app.delete_json_api(
            public_url,
            {'data': {
                'id': public_project._id,
                'type': 'node_links'
            }},
            auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    #   test_bulk_delete_pointers_no_type
        payload = {'data': [
            {'id': public_project_pointer_project_one._id},
            {'id': public_project_pointer_project_two._id}
        ]}
        res = app.delete_json_api(
            public_url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_bulk_delete_pointers_incorrect_type
        payload = {'data': [
            {'id': public_pointer_one._id, 'type': 'Incorrect type.'},
            {'id': public_pointer_two._id, 'type': 'Incorrect type.'}
        ]}
        res = app.delete_json_api(
            public_url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 409

    #   test_bulk_delete_pointers_no_id
        payload = {'data': [
            {'type': 'node_links'},
            {'type': 'node_links'}
        ]}
        res = app.delete_json_api(
            public_url, payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_bulk_delete_pointers_no_data
        res = app.delete_json_api(
            public_url, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must contain array of resource identifier objects.'

    #   test_bulk_delete_pointers_payload_is_empty_dict
        res = app.delete_json_api(
            public_url, {}, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'

    #   test_bulk_deletes_public_node_pointers_logged_out
        res = app.delete_json_api(
            public_url, public_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_deletes_public_node_pointers_fails_if_bad_auth
        node_count_before = len(public_project.nodes_pointer)
        res = app.delete_json_api(
            public_url, public_payload,
            auth=non_contrib.auth,
            expect_errors=True, bulk=True)
        # This is could arguably be a 405, but we don't need to go crazy with
        # status codes
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]
        public_project.reload()
        assert node_count_before == len(public_project.nodes_pointer)

    #   test_bulk_deletes_private_node_pointers_logged_in_non_contributor
        res = app.delete_json_api(
            private_url, private_payload,
            auth=non_contrib.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_bulk_deletes_private_node_pointers_logged_out
        res = app.delete_json_api(
            private_url, private_payload,
            expect_errors=True, bulk=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_cannot_delete_if_registration(
            self, app, user, public_project, public_payload):
        registration = RegistrationFactory(project=public_project)

        url = '/{}registrations/{}/node_links/'.format(
            API_BASE, registration._id)

        res = app.delete_json_api(
            url, public_payload, auth=user.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 405

    def test_bulk_deletes_public_node_pointers_succeeds_as_owner(
            self, app, user, public_project, public_url, public_payload):
        with assert_latest_log(NodeLog.POINTER_REMOVED, public_project):
            node_count_before = len(public_project.nodes_pointer)
            res = app.delete_json_api(
                public_url, public_payload, auth=user.auth, bulk=True)
            public_project.reload()
            assert res.status_code == 204
            assert node_count_before - 2 == len(public_project.nodes_pointer)

            public_project.reload()

    def test_bulk_deletes_private_node_pointers_logged_in_contributor(
            self, app, user, private_project, private_url, private_payload):
        with assert_latest_log(NodeLog.POINTER_REMOVED, private_project):
            res = app.delete_json_api(
                private_url, private_payload,
                auth=user.auth, bulk=True)
            private_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204
            assert len(private_project.nodes_pointer) == 0

    def test_return_bulk_deleted_public_node_pointer(
            self, app, user, public_project,
            public_pointer_one, public_url, public_payload):
        with assert_latest_log(NodeLog.POINTER_REMOVED, public_project):
            res = app.delete_json_api(
                public_url, public_payload, auth=user.auth, bulk=True)
            public_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204

            pointer_url = '/{}nodes/{}/node_links/{}/'.format(
                API_BASE, public_project._id, public_pointer_one._id)

            # check that deleted pointer can not be returned
            res = app.get(pointer_url, auth=user.auth, expect_errors=True)
            assert res.status_code == 404

    def test_return_bulk_deleted_private_node_pointer(
            self, app, user, private_project, private_pointer_one,
            private_url, private_payload):
        with assert_latest_log(NodeLog.POINTER_REMOVED, private_project):
            res = app.delete_json_api(
                private_url, private_payload,
                auth=user.auth, bulk=True)
            private_project.reload()  # Update the model to reflect changes made by post request
            assert res.status_code == 204

            pointer_url = '/{}nodes/{}/node_links/{}/'.format(
                API_BASE, private_project._id, private_pointer_one._id)

            # check that deleted pointer can not be returned
            res = app.get(pointer_url, auth=user.auth, expect_errors=True)
            assert res.status_code == 404

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_bulk_delete_link_that_is_not_linked_to_correct_node(
            self, app, user, private_url, public_payload):
        ProjectFactory(creator=user)
        # The node link belongs to a different project
        res = app.delete_json_api(
            private_url, public_payload, auth=user.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Node link does not belong to the requested node.'
