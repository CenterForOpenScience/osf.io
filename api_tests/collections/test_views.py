from urlparse import urlparse

from nose.tools import *  # flake8: noqa

from website.models import Node, NodeLog
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    FolderFactory,
    NodeFactory,
    ProjectFactory,
    AuthUserFactory
)
from tests.utils import assert_logs
from framework.auth.core import Auth


def node_url_for(node_id):
    return '/{}nodes/{}/'.format(API_BASE, node_id)


class TestCollectionList(ApiTestCase):
    def setUp(self):
        super(TestCollectionList, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.deleted_one = FolderFactory(creator=self.user_one, is_deleted=True)
        self.collection_one = FolderFactory(creator=self.user_one)

        self.url = '/{}collections/'.format(API_BASE)

    def user_one_gets_user_one_collections(self):
        res = self.app.get(self.url, auth=self.user_one)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.deleted_one._id, ids)
        assert_in(self.collection_one._id, ids)

    def user_two_gets_nothing(self):
        res = self.app.get(self.url, auth=self.user_two)
        ids = [each['id'] for each in res.json['data']]
        assert_not_in(self.deleted_one._id, ids)
        assert_not_in(self.collection_one._id, ids)

    def test_unauthorized_gets_nothing(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_not_in(self.deleted_one._id, ids)
        assert_not_in(self.collection_one._id, ids)


class TestCollectionCreate(ApiTestCase):

    def setUp(self):
        super(TestCollectionCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}collections/'.format(API_BASE)

        self.title = 'Cool Collection'

        self.user_two = AuthUserFactory()

        self.collection = {
            'data': {
                'type': 'collections',
                'attributes':
                    {
                        'title': self.title,
                    }
            }
        }

    def test_collection_create_invalid_data(self):
        res = self.app.post_json_api(self.url, "Incorrect data", auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.post_json_api(self.url, ["Incorrect data"], auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_creates_collection_logged_out(self):
        res = self.app.post_json_api(self.url, self.collection, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_collection_logged_in(self):
        res = self.app.post_json_api(self.url, self.collection, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        pid = res.json['data']['id']
        assert_equal(res.json['data']['attributes']['title'], self.title)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['type'], 'collections')
        res = self.app.get(self.url+'?filter[title]={}'.format(self.title), auth=self.user_one.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(pid, ids)
        collection = Node.load(pid)
        assert_equal(collection.logs[-1].action, NodeLog.PROJECT_CREATED)
        assert_equal(collection.title, self.title)

    def test_create_collection_creates_collection_and_sanitizes_html(self):
        title = '<em>Cool</em> <script>alert("even cooler")</script> <strong>Project</strong>'

        res = self.app.post_json_api(self.url, {
            'data': {
                'attributes': {
                    'title': title,
                },
                'type': 'collections'
            }
        }, auth=self.user_one.auth)
        collection_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')

        collection = Node.load(collection_id)
        assert_equal(collection.logs[-1].action, NodeLog.PROJECT_CREATED)
        assert_equal(collection.title, strip_html(title))

    def test_creates_project_no_type(self):
        collection = {
            'data': {
                'attributes': {
                    'title': self.title,
                }
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_creates_project_incorrect_type(self):
        collection = {
            'data': {
                'attributes': {
                    'title': self.title,
                },
                'type': 'Wrong type.'
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

    def test_creates_collection_properties_not_nested(self):
        project = {
            'data': {
                'title': self.title,
                'type': 'collections'
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/attributes.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

    def test_create_project_invalid_title(self):
        project = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'A' * 201,
                }
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')


class TestCollectionFiltering(ApiTestCase):

    def setUp(self):
        super(TestCollectionFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection_one = FolderFactory(title="Collection One", creator=self.user_one)
        self.collection_two = FolderFactory(title="Collection Two", creator=self.user_one)
        self.collection_three = FolderFactory(title="Three", creator=self.user_one)

        self.url = "/{}collections/".format(API_BASE)

    def test_get_all_projects_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_in(self.collection_three._id, ids)

    def test_get_no_collections_with_no_filter_not_logged_in(self):
        res = self.app.get(self.url)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_get_no_collections_with_no_filter_logged_in_as_wrong_user(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_get_one_collection_with_exact_filter_logged_in(self):
        url = "/{}collections/?filter[title]=Collection%20One".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_get_one_collection_with_exact_filter_not_logged_in(self):
        url = "/{}collections/?filter[title]=Collection%20One".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_get_some_collections_with_substring_logged_in(self):
        url = "/{}collections/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_get_no_projects_with_substring_not_logged_in(self):
        url = "/{}collections/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.collection_one._id, ids)
        assert_not_in(self.collection_two._id, ids)
        assert_not_in(self.collection_three._id, ids)

    def test_incorrect_filtering_field_logged_in(self):
        url = '/{}collections/?filter[notafield]=bogus'.format(API_BASE)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'notafield' is not a valid field for this endpoint.")
        assert_equal(errors[0]['source'], {'parameter': 'filter'})


class TestCollectionDetail(ApiTestCase):
    def setUp(self):
        super(TestCollectionDetail, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.collection = FolderFactory(title="Test collection", creator=self.user_one)
        self.url = '/{}collections/{}/'.format(API_BASE, self.collection._id)

    def test_do_not_return_collection_details_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_collection_details_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.collection.title)
        node_links_url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = self.url + 'node_links/'
        assert_equal(urlparse(node_links_url).path, expected_url)

    def test_do_not_return_collection_details_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_requesting_node_returns_error(self):
        node = NodeFactory(creator=self.user_one)
        res = self.app.get(
            '/{}collections/{}/'.format(API_BASE, node._id),
            auth=self.user_one.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)


class CollectionCRUDTestCase(ApiTestCase):

    def setUp(self):
        super(CollectionCRUDTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.title = 'Cool Collection'
        self.new_title = 'Super Cool Collection'

        self.collection = FolderFactory(title=self.title, creator=self.user)
        self.url = '/{}collections/{}/'.format(API_BASE, self.collection._id)
        self.fake_url = '/{}collections/{}/'.format(API_BASE, '12345')


def make_collection_payload(collection, attributes):
    return {
        'data': {
            'id': collection._id,
            'type': 'collections',
            'attributes': attributes,
        }
    }


class TestCollectionUpdate(CollectionCRUDTestCase):

    def test_node_update_invalid_data(self):
        res = self.app.put_json_api(self.url, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.patch_json_api(self.url, ["Incorrect data"], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_update_collection_properties_not_nested(self):
        res = self.app.put_json_api(self.url, {
            'id': self.collection._id,
            'type': 'collections',
            'title': self.new_title,
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_update_invalid_id(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': '12345',
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_invalid_type(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collection',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_no_id(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_update_no_type(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_cannot_update_collection_logged_out(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.EDITED_TITLE, 'collection')
    def test_update_collection_logged_in(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        self.collection.reload()
        assert_equal(self.collection.title, self.new_title)

    @assert_logs(NodeLog.EDITED_TITLE, 'collection')
    def test_partial_update_collection_logged_in(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        self.collection.reload()
        assert_equal(self.collection.title, self.new_title)

    def test_cannot_update_collection_logged_in_but_unauthorized(self):
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.EDITED_TITLE, 'collection')
    def test_update_collection_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong><script>alert("even cooler")</script> Cool Project'
        res = self.app.put_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        self.collection.reload()
        assert_equal(self.collection.title, strip_html(new_title))

    @assert_logs(NodeLog.EDITED_TITLE, 'collection')
    def test_partial_update_collection_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        res = self.app.patch_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        self.collection.reload()
        assert_equal(self.collection.title, strip_html(new_title))

    def test_partial_update_collection_logged_in_but_unauthorized(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.collection._id,
                'type': 'nodes',
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_multiple_patch_requests_with_same_title_generates_one_log(self):
        payload = make_collection_payload(collection=self.collection, attributes={'title': self.new_title})
        original_n_logs = len(self.collection.logs)

        for x in range(0, 2):
            res = self.app.patch_json_api(self.url, payload, auth=self.user.auth)
            assert_equal(res.status_code, 200)
            self.collection.reload()
            assert_equal(self.collection.title, self.new_title)
            assert_equal(len(self.collection.logs), original_n_logs + 1)  # sanity check

    def test_partial_update_invalid_id(self):
        res = self.app.patch_json_api(self.url, {
                'data': {
                    'id': '12345',
                    'type': 'collections',
                    'attributes': {
                        'title': self.new_title,
                    }
                }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_invalid_type(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'collection',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_no_id(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_partial_update_no_type(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    # Nothing will be updated here
    def test_partial_update_collection_properties_not_nested(self):
        res = self.app.patch_json_api(self.url, {
            'data': {
                'id': self.collection._id,
                'type': 'nodes',
                'title': self.new_title,
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_collection_invalid_title(self):
        project = {
            'data': {
                'type': 'collections',
                'id': self.collection._id,
                'attributes': {
                    'title': 'A' * 201,
                    'category': 'project',
                }
            }
        }
        res = self.app.put_json_api(self.url, project, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')


class TestCollectionDelete(CollectionCRUDTestCase):

    def test_do_not_delete_collection_unauthenticated(self):
        res = self.app.delete(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_do_not_return_deleted_collection(self):
        self.collection.is_deleted = True
        self.collection.save()
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 410)
        assert 'detail' in res.json['errors'][0]

    def test_do_not_delete_collection_unauthorized(self):
        res = self.app.delete_json_api(self.url, auth=self.user_two.auth, expect_errors=True)
        self.collection.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.collection.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.PROJECT_DELETED, 'collection')
    def test_delete_collection_authorized(self):
        res = self.app.delete_json_api(self.url, auth=self.user.auth, expect_errors=True)
        self.collection.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.collection.is_deleted, True)

    def test_cannot_delete_invalid_collection(self):
        res = self.app.delete(self.fake_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]


class TestCollectionNodeLinksList(ApiTestCase):

    def setUp(self):
        super(TestCollectionNodeLinksList, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection = FolderFactory(creator=self.user_one)
        self.project = ProjectFactory(is_public=False, creator=self.user_one)
        self.public_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.private_project = ProjectFactory(is_public=False, creator=self.user_two)
        self.collection.add_pointer(self.project, auth=Auth(self.user_one))
        self.collection.add_pointer(self.public_project, auth=Auth(self.user_one))
        self.url = '/{}collections/{}/node_links/'.format(API_BASE, self.collection._id)

    def test_do_not_return_node_pointers_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_node_pointers_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 2)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_project_path = node_url_for(self.project._id)
        expected_public_project_path = node_url_for(self.public_project._id)
        actual_project_path = urlparse(res_json[0]['relationships']['target_node']['links']['related']['href']).path
        actual_public_project_path = urlparse(res_json[1]['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_project_path, actual_project_path)
        assert_equal(expected_public_project_path, actual_public_project_path)

    def test_return_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_deleted_links_not_returned(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        res_json = res.json['data']
        original_length = len(res_json)

        self.public_project.is_deleted = True
        self.public_project.save()

        res = self.app.get(self.url, auth=self.user_one.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), original_length - 1)


class TestCollectionNodeLinkCreate(ApiTestCase):

    def setUp(self):
        super(TestCollectionNodeLinkCreate, self).setUp()
        node_link_string = '/{}collections/{}/node_links/'
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.collection = FolderFactory(creator=self.user_one)
        self.collection_two = FolderFactory(creator=self.user_one)

        self.project = ProjectFactory(is_public=False, creator=self.user_one)
        self.public_project = ProjectFactory(is_public=True, creator=self.user_one)
        self.user_two_private_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_public_project = ProjectFactory(is_public=False, creator=self.user_two)

        self.url = node_link_string.format(API_BASE, self.collection._id)
        self.fake_node_id = 'fakeident'
        self.fake_url = node_link_string.format(API_BASE, self.fake_node_id)

    @staticmethod
    def post_payload(target_node_id, outer_type='node_links', inner_type='nodes'):
        payload = {
            'data': {
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': target_node_id,
                        }
                    }
                }
            }
        }

        if outer_type:
            payload['data']['type'] = outer_type
        if inner_type:
            payload['data']['relationships']['nodes']['data']['type'] = inner_type
        return payload

    def test_does_not_create_link_when_payload_not_nested(self):
        payload = {'data': {'type': 'node_links', 'target_node_id': self.project._id}}
        res = self.app.post_json_api(self.url, payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')

    def test_does_not_create_node_link_logged_out(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.project._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'collection')
    def test_creates_node_link_to_public_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.public_project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.public_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    @assert_logs(NodeLog.POINTER_CREATED, 'collection')
    def test_creates_node_link_to_private_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        res_json = res.json['data']
        expected_path = node_url_for(self.project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_does_not_create_node_link_unauthorized(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.user_two_private_project._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'collection')
    def test_create_node_link_to_non_contributing_node(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.user_two_public_project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.user_two_public_project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_create_node_link_to_fake_node(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.fake_node_id), auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])
        assert_in('source', res.json['errors'][0])

    def test_fake_collection_pointing_to_valid_node(self):
        res = self.app.post_json_api(self.fake_url, self.post_payload(self.project._id), auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(self.fake_url, self.post_payload(self.project._id), auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_create_collection_node_pointer_to_itself(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.collection._id), auth=self.user_one.auth, expect_errors=True)
        res_json = res.json
        assert_equal(res.status_code, 400)
        error = res_json['errors'][0]
        assert_in('detail', error)
        assert_equal("Target Node '{}' not found.".format(self.collection._id), error['detail'])
        assert_in('source', error)
        assert_in('pointer', error['source'])
        assert_equal('/data/relationships/node_links/data/id', error['source']['pointer'])

    @assert_logs(NodeLog.POINTER_CREATED, 'collection')
    def test_create_node_pointer_already_connected(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        expected_path = node_url_for(self.project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

        res = self.app.post_json_api(self.url, self.post_payload(self.project._id), auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        error = res.json['errors'][0]
        assert_in('detail', error)
        assert_equal('Target Node \'{}\' already pointed to by \'{}\'.'.format(self.project._id, self.collection._id), error['detail'])
        assert_in('source', error)
        assert_in('pointer', error['source'])
        assert_equal('/data/relationships/node_links/data/id', error['source']['pointer'])

    def test_create_node_pointer_no_type(self):
        payload = self.post_payload(self.public_project._id, outer_type=None)
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_node_pointer_incorrect_type(self):
        payload = self.post_payload(self.public_project._id, outer_type='wrong_type')
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')


class TestCollectionNodeLinkDetail(ApiTestCase):

    def setUp(self):
        super(TestCollectionNodeLinkDetail, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection = FolderFactory(creator=self.user_one)
        self.project = ProjectFactory(creator=self.user_one, is_public=False)
        self.project_public = ProjectFactory(creator=self.user_one, is_public=False)
        self.node_link = self.collection.add_pointer(self.project, auth=Auth(self.user_one), save=True)
        self.node_link_public = self.collection.add_pointer(self.project_public, auth=Auth(self.user_one), save=True)
        self.url = '/{}collections/{}/node_links/{}/'.format(API_BASE, self.collection._id, self.node_link._id)
        self.url_public = '/{}collections/{}/node_links/{}/'.format(API_BASE, self.collection._id, self.node_link_public._id)

    def test_returns_error_public_node_link_detail_unauthenticated(self):
        res = self.app.get(self.url_public, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_public_node_pointer_detail_authorized(self):
        res = self.app.get(self.url_public, auth=self.user_one.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.project_public._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_returns_error_private_node_link_detail_unauthenticated(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_node_link_detail_authorized(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        expected_path = node_url_for(self.project._id)
        actual_path = urlparse(res_json['relationships']['target_node']['links']['related']['href']).path
        assert_equal(expected_path, actual_path)

    def test_returns_error_private_node_link_detail_unauthorized(self):
        res = self.app.get(self.url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_self_link_points_to_node_link_detail_url(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        url = res.json['data']['links']['self']
        assert_in(self.url, url)

    def test_delete_node_link_no_permissions_for_target_node(self):
        pointer_project = FolderFactory(creator=self.user_two)
        pointer = self.collection.add_pointer(pointer_project, auth=Auth(self.user_one), save=True)
        assert_in(pointer, self.collection.nodes)
        url = '/{}collections/{}/node_links/{}/'.format(API_BASE, self.collection._id, pointer._id)
        res = self.app.delete_json_api(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 204)

    def test_can_not_delete_collection_public_node_link_unauthenticated(self):
        res = self.app.delete(self.url_public, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0].keys())

    def test_can_not_delete_collection_public_node_pointer_unauthorized(self):
        node_count_before = len(self.collection.nodes_pointer)
        res = self.app.delete(self.url_public, auth=self.user_two.auth, expect_errors=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])
        self.collection.reload()
        assert_equal(node_count_before, len(self.collection.nodes_pointer))

    @assert_logs(NodeLog.POINTER_REMOVED, 'collection')
    def test_delete_public_node_pointer_authorized(self):
        node_count_before = len(self.collection.nodes_pointer)
        res = self.app.delete(self.url_public, auth=self.user_one.auth)
        self.collection.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.collection.nodes_pointer))

    @assert_logs(NodeLog.POINTER_REMOVED, 'collection')
    def test_delete_private_node_link_authorized(self):
        node_count_before = len(self.collection.nodes_pointer)
        res = self.app.delete(self.url, auth=self.user_one.auth)
        self.collection.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.collection.nodes_pointer))

    def test_can_not_delete_collection_private_node_link_unauthorized(self):
        res = self.app.delete(self.url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'collection')
    def test_can_not_return_deleted_collection_public_node_pointer(self):
        res = self.app.delete(self.url_public, auth=self.user_one.auth)
        self.collection.reload()
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url_public, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.POINTER_REMOVED, 'collection')
    def test_return_deleted_private_node_pointer(self):
        res = self.app.delete(self.url, auth=self.user_one.auth)
        self.project.reload()
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_delete_link_that_is_not_linked_to_correct_node(self):
        collection = FolderFactory(creator=self.user_one)
        # The node link belongs to a different project
        res = self.app.delete(
            '/{}nodes/{}/node_links/{}/'.format(API_BASE, collection._id, self.node_link._id),
            auth=self.user_one.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Not found.')


class TestReturnDeletedCollection(ApiTestCase):
    def setUp(self):

        super(TestReturnDeletedCollection, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.deleted = FolderFactory(is_deleted=True, creator=self.user, title='This collection has been deleted')
        self.collection = FolderFactory(creator=self.user, title='A boring collection')

        self.new_title = 'This deleted node has been edited'
        self.deleted_url = '/{}collections/{}/'.format(API_BASE, self.deleted._id)

    def test_return_deleted_collection(self):
        res = self.app.get(self.deleted_url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_collection(self):
        res = self.app.put_json_api(self.deleted_url, params={'title': self.new_title}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_collection(self):
        res = self.app.delete(self.deleted_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

