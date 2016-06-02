from urlparse import urlparse

from nose.tools import *  # flake8: noqa

from website.models import Node, NodeLog
from website.util.sanitize import strip_html
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    CollectionFactory,
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
        self.deleted_one = CollectionFactory(creator=self.user_one, is_deleted=True)
        self.collection_one = CollectionFactory(creator=self.user_one)

        self.url = '/{}collections/'.format(API_BASE)

    def test_user_one_gets_user_one_collections(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_not_in(self.deleted_one._id, ids)
        assert_in(self.collection_one._id, ids)

    def test_user_two_gets_nothing(self):
        res = self.app.get(self.url, auth=self.user_two.auth)
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
        assert_equal(res.json['errors'][0]['detail'], 'The resource type you specified "Wrong type." does not match the type of the resource you specified "collections".')

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

    def test_create_bookmark_collection(self):
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], 'Bookmarks')
        assert_true(res.json['data']['attributes']['bookmarks'])

    def test_cannot_create_multiple_bookmark_collection(self):
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Each user cannot have more than one Bookmark collection.')

    def test_create_bookmark_collection_with_wrong_title(self):
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Not Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], 'Bookmarks')
        assert_true(res.json['data']['attributes']['bookmarks'])

    def test_create_bookmark_collection_with_no_title(self):
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'bookmarks': True,
                }
            }
        }
        res = self.app.post_json_api(self.url, collection, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

class TestCollectionFiltering(ApiTestCase):

    def setUp(self):
        super(TestCollectionFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection_one = CollectionFactory(title="Collection One", creator=self.user_one)
        self.collection_two = CollectionFactory(title="Collection Two", creator=self.user_one)
        self.collection_three = CollectionFactory(title="Three", creator=self.user_one)

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

        self.collection = CollectionFactory(title="Test collection", creator=self.user_one)
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

        self.collection = CollectionFactory(title=self.title, creator=self.user)
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
        self.collection = CollectionFactory(creator=self.user_one)
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
        first_embedded = res_json[0]['embeds']['target_node']['data']['id']
        second_embedded = res_json[1]['embeds']['target_node']['data']['id']
        assert_items_equal([first_embedded, second_embedded], [self.project._id, self.public_project._id])

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

        self.collection = CollectionFactory(creator=self.user_one)
        self.collection_two = CollectionFactory(creator=self.user_one)

        self.project = ProjectFactory(is_public=False, creator=self.user_one)
        self.public_project = ProjectFactory(is_public=True, creator=self.user_one)
        self.user_two_private_project = ProjectFactory(is_public=False, creator=self.user_two)
        self.user_two_public_project = ProjectFactory(is_public=True, creator=self.user_two)

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
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded_node_id, self.public_project._id)

    @assert_logs(NodeLog.POINTER_CREATED, 'collection')
    def test_creates_node_link_to_private_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.post_payload(self.project._id), auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        res_json = res.json['data']
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded_node_id, self.project._id)

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
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded_node_id, self.user_two_public_project._id)

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
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded_node_id, self.project._id)

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
        assert_equal(res.json['errors'][0]['detail'], 'The resource type you specified "wrong_type" does not match the type of the resource you specified "node_links".')


class TestCollectionNodeLinkDetail(ApiTestCase):

    def setUp(self):
        super(TestCollectionNodeLinkDetail, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection = CollectionFactory(creator=self.user_one)
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
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.project_public._id)

    def test_returns_error_private_node_link_detail_unauthenticated(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_node_link_detail_authorized(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        embedded = res_json['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.project._id)

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
        pointer_project = CollectionFactory(creator=self.user_two)
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
        collection = CollectionFactory(creator=self.user_one)
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

        self.deleted = CollectionFactory(is_deleted=True, creator=self.user, title='This collection has been deleted')
        self.collection = CollectionFactory(creator=self.user, title='A boring collection')

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


class TestCollectionBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestCollectionBulkCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}collections/'.format(API_BASE)

        self.title = 'Cool Collection'
        self.title_two = 'Cool Collection, Too'

        self.user_two = AuthUserFactory()

        self.collection = {
                'type': 'collections',
                'attributes': {
                    'title': self.title,
                }
        }
        
        self.collection_two = {
                'type': 'collections',
                'attributes': {
                    'title': self.title_two,
                }
        }

        self.empty_collection = {'type': 'collections', 'attributes': {'title': "",}}

    def test_bulk_create_collections_blank_request(self):
        res = self.app.post_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_create_all_or_nothing(self):
        res = self.app.post_json_api(self.url, {'data': [self.collection, self.empty_collection]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_out(self):
        res = self.app.post_json_api(self.url, {'data': [self.collection, self.collection_two]}, bulk=True, expect_errors=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_error_formatting(self):
        res = self.app.post_json_api(self.url, {'data': [self.empty_collection, self.empty_collection]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ["This field may not be blank.", "This field may not be blank."])

    def test_bulk_create_limits(self):
        node_create_list = {'data': [self.collection] * 101}
        res = self.app.post_json_api(self.url, node_create_list, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_type(self):
        payload = {'data': [{"attributes": {'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_incorrect_type(self):
        payload = {'data': [self.collection, {'type': 'Incorrect type.', 'attributes': {'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_attributes(self):
        payload = {'data': [self.collection, {'type': 'collections', }]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_title(self):
        payload = {'data': [self.collection, {'type': 'collections', "attributes": {}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/attributes/title')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_ugly_payload(self):
        payload = 'sdf;jlasfd'
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_in(self):
        res = self.app.post_json_api(self.url, {'data': [self.collection, self.collection_two]}, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['attributes']['title'], self.collection['attributes']['title'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.collection_two['attributes']['title'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 2)
        id_one = res.json['data'][0]['id']
        id_two = res.json['data'][1]['id']

        res = self.app.delete_json_api(self.url, {'data': [{'id': id_one, 'type': 'collections'},
                                                           {'id': id_two, 'type': 'collections'}]},
                                       auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 204)


class TestCollectionBulkUpdate(ApiTestCase):

    def setUp(self):
        super(TestCollectionBulkUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'

        self.collection = CollectionFactory(title=self.title,
                                            creator=self.user)

        self.collection_two = CollectionFactory(title=self.title,
                                                creator=self.user)

        self.collection_payload = {
            'data': [
                {
                    'id': self.collection._id,
                    'type': 'collections',
                    'attributes': {
                        'title': self.new_title,
                    }
                },
                {
                    'id': self.collection_two._id,
                    'type': 'collections',
                    'attributes': {
                        'title': self.new_title,
                    }
                }
            ]
        }

        self.url = '/{}collections/'.format(API_BASE)
        self.detail_url_base = '/{}collections/{}/'

        self.empty_payload = {'data': [
            {'id': self.collection._id, 'type': 'collections', 'attributes': {'title': "",}},
            {'id': self.collection_two._id, 'type': 'collections', 'attributes': {'title': "",}}
        ]}

    def test_bulk_update_nodes_blank_request(self):
        res = self.app.put_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_update_blank_but_not_empty_title(self):
        payload = {
            "data": [
                {
                  "id": self.collection._id,
                  "type": "collections",
                  "attributes": {
                    "title": "This shouldn't update."
                  }
                },
                {
                  "id": self.collection_two._id,
                  "type": "collections",
                  "attributes": {
                    "title": " "
                  }
                }
              ]
            }
        url = self.detail_url_base.format(API_BASE, self.collection._id)
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_collections_one_not_found(self):
        empty_payload = {'data': [
            {
                'id': 12345,
                'type': 'collections',
                'attributes': {
                    'title': self.new_title
                }
            }, self.collection_payload['data'][0]
        ]}

        res = self.app.put_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

        url = self.detail_url_base.format(API_BASE, self.collection._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_collections_logged_out(self):
        res = self.app.put_json_api(self.url, self.collection_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = self.detail_url_base.format(API_BASE, self.collection._id)
        url_two = self.detail_url_base.format(API_BASE, self.collection_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_collections_logged_in(self):
        res = self.app.put_json_api(self.url, self.collection_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.collection._id, self.collection_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_update_collections_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.url, {'data': {'id': self.collection._id, 'type': 'nodes',
                                                        'attributes': {'title': self.new_title}}},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_update_error_formatting(self):
        res = self.app.put_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.'] * 2)

    def test_bulk_update_id_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.collection_payload['data'][1], {'type': 'collections', 'attributes':
            {'title': self.new_title}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/id')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = self.detail_url_base.format(API_BASE, self.collection_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_type_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.collection_payload['data'][1], {'id': self.collection._id, 'attributes':
            {'title': self.new_title}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/type')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = self.detail_url_base.format(API_BASE, self.collection_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_incorrect_type(self):
        res = self.app.put_json_api(self.url, {'data': [self.collection_payload['data'][1], {'id': self.collection._id, 'type': 'Incorrect', 'attributes':
            {'title': self.new_title}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        url = self.detail_url_base.format(API_BASE, self.collection_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_limits(self):
        node_update_list = {'data': [self.collection_payload['data'][0]] * 101}
        res = self.app.put_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_update_no_title(self):
        new_payload = {'id': self.collection._id, 'type': 'collections', 'attributes': {}}
        res = self.app.put_json_api(self.url, {'data': [self.collection_payload['data'][1], new_payload]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        url = self.detail_url_base.format(API_BASE, self.collection_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)


class TestNodeBulkDelete(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkDelete, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.collection_one = CollectionFactory(title="Collection One", creator=self.user_one)
        self.collection_two = CollectionFactory(title="Collection Two", creator=self.user_one)
        self.collection_three = CollectionFactory(title="Collection Three", creator=self.user_one)
        self.collection_user_two = CollectionFactory(title="Collection User Two", creator=self.user_two)

        self.url = "/{}collections/".format(API_BASE)
        self.project_one_url = '/{}collections/{}/'.format(API_BASE, self.collection_one._id)
        self.project_two_url = '/{}collections/{}/'.format(API_BASE, self.collection_two._id)
        self.private_project_url = "/{}collections/{}/".format(API_BASE, self.collection_three._id)

        self.payload_one = {'data': [{'id': self.collection_one._id, 'type': 'collections'},
                                     {'id': self.collection_two._id, 'type': 'collections'}]}
        self.payload_two = {'data': [{'id': self.collection_three._id, 'type': 'collections'}]}

    def test_bulk_delete_nodes_blank_request(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_no_type(self):
        payload = {'data': [
            {'id': self.collection_one._id},
            {'id': self.collection_two._id}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')

    def test_bulk_delete_no_id(self):
        payload = {'data': [
            {'type': 'collections'}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/id.')

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.url, {'data': {'id': self.collection_one._id, 'type': 'collections'}},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_invalid_type(self):
        res = self.app.delete_json_api(self.url, {'data': [{'type': 'Wrong type', 'id': self.collection_one._id}]},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_collections_logged_in(self):
        res = self.app.delete_json_api(self.url, self.payload_one, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.collection_one.reload()
        self.collection_two.reload()

    def test_bulk_delete_collections_logged_out(self):
        res = self.app.delete_json_api(self.url, self.payload_one, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.get(self.project_two_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_collections_logged_in_non_contributor(self):
        res = self.app.delete_json_api(self.url, self.payload_two,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_all_or_nothing(self):
        new_payload = {'data': [{'id': self.collection_three._id, 'type': 'collections'}, {'id': self.collection_user_two
            ._id, 'type': 'collections'}]}
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

        url = "/{}collections/{}/".format(API_BASE, self.collection_user_two._id)
        res = self.app.get(url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_limits(self):
        new_payload = {'data': [{'id': self.collection_three._id, 'type': 'nodes'}] * 101}
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_invalid_payload_one_not_found(self):
        new_payload = {'data': [self.payload_one['data'][0], {'id': '12345', 'type': 'collections'}]}
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to delete.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_no_payload(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)


class TestCollectionLinksBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestCollectionLinksBulkCreate, self).setUp()
        self.user = AuthUserFactory()

        self.collection_one = CollectionFactory(is_public=False, creator=self.user)
        self.private_pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_pointer_project_two = ProjectFactory(is_public=False, creator=self.user)

        self.collection_url = '/{}collections/{}/node_links/'.format(API_BASE, self.collection_one._id)

        self.collection_payload = {
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

        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project_two = ProjectFactory(is_public=True, creator=self.user)

        self.user_two = AuthUserFactory()
        self.user_two_collection = CollectionFactory(creator=self.user_two)
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}collections/{}/node_links/'.format(API_BASE, self.user_two_collection._id)
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
        res = self.app.post_json_api(self.collection_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_creates_pointers_limits(self):
        payload = {'data': [self.collection_payload['data'][0]] * 101}
        res = self.app.post_json_api(self.collection_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

        res = self.app.get(self.collection_url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_bulk_creates_project_target_not_nested(self):
        payload = {'data': [{'type': 'node_links', 'target_node_id': self.private_pointer_project._id}]}
        res = self.app.post_json_api(self.collection_url, payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')

    def test_bulk_creates_collection_node_pointers_logged_out(self):
        res = self.app.post_json_api(self.collection_url, self.collection_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

        res = self.app.get(self.collection_url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_bulk_creates_collection_node_pointer_logged_in_non_contrib(self):
        res = self.app.post_json_api(self.collection_url, self.collection_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

    def test_bulk_creates_collection_node_pointer_logged_in_contrib(self):
        res = self.app.post_json_api(self.collection_url, self.collection_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.private_pointer_project._id)

        embedded = res_json[1]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.private_pointer_project_two._id)

    def test_bulk_creates_node_pointers_collection_to_non_contributing_node(self):
        res = self.app.post_json_api(self.collection_url, self.user_two_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.user_two_project._id)

        res = self.app.get(self.collection_url, auth=self.user.auth)
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.user_two_project._id)

    def test_bulk_creates_pointers_non_contributing_node_to_fake_node(self):
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = self.app.post_json_api(self.collection_url, fake_payload,
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_creates_pointers_contributing_node_to_fake_node(self):
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = self.app.post_json_api(self.collection_url, fake_payload,
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_creates_fake_nodes_pointing_to_contributing_node(self):
        fake_url = '/{}collections/{}/node_links/'.format(API_BASE, 'fdxlq')

        res = self.app.post_json_api(fake_url, self.collection_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(fake_url, self.collection_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_creates_node_pointer_already_connected(self):
        res = self.app.post_json_api(self.collection_url, self.collection_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert_equal(embedded, self.private_pointer_project._id)

        embedded_two = res_json[1]['embeds']['target_node']['data']['id']
        assert_equal(embedded_two, self.private_pointer_project_two._id)

        res = self.app.post_json_api(self.collection_url, self.collection_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_in("Target Node '{}' already pointed to by '{}'.".format(self.private_pointer_project._id, self.collection_one._id), res.json['errors'][0]['detail'])

    def test_bulk_creates_node_pointer_no_type(self):
        payload = {'data': [{'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.user_two_collection._id}}}}]}
        res = self.app.post_json_api(self.collection_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')

    def test_bulk_creates_node_pointer_incorrect_type(self):
        payload = {'data': [{'type': 'Wrong type.', 'relationships': {'nodes': {'data': {'type': 'nodes', 'id': self.user_two_collection._id}}}}]}
        res = self.app.post_json_api(self.collection_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'The resource type you specified "Wrong type." does not match the type of the resource you specified "node_links".')


class TestBulkDeleteCollectionNodeLinks(ApiTestCase):

    def setUp(self):
        super(TestBulkDeleteCollectionNodeLinks, self).setUp()
        self.user = AuthUserFactory()
        self.collection = CollectionFactory(creator=self.user)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True)
        self.pointer_project_two = ProjectFactory(creator=self.user, is_public=True)

        self.pointer = self.collection.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.pointer_two = self.collection.add_pointer(self.pointer_project_two, auth=Auth(self.user), save=True)

        self.collection_payload = {
              "data": [
                {"type": "node_links", "id": self.pointer._id},
                {"type": "node_links", "id": self.pointer_two._id}
              ]
            }

        self.collection_url = '/{}collections/{}/node_links/'.format(API_BASE, self.collection._id)

        self.user_two = AuthUserFactory()

        self.collection_two = CollectionFactory(creator=self.user)
        self.collection_two_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.collection_two_pointer_project_two = ProjectFactory(is_public=True, creator=self.user)

        self.collection_two_pointer = self.collection_two.add_pointer(self.collection_two_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.collection_two_pointer_two = self.collection_two.add_pointer(self.collection_two_pointer_project_two,
                                                              auth=Auth(self.user),
                                                              save=True)

        self.collection_two_payload = {
              'data': [
                {'type': 'node_links', 'id': self.collection_two_pointer._id},
                {'type': 'node_links', 'id': self.collection_two_pointer_two._id}
              ]
            }

        self.collection_two_url = '/{}collections/{}/node_links/'.format(API_BASE, self.collection_two._id)

    def test_bulk_delete_node_links_blank_request(self):
        res = self.app.delete_json_api(self.collection_two_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_pointer_limits(self):
        res = self.app.delete_json_api(self.collection_two_url, {'data': [self.collection_two_payload['data'][0]] * 101},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.collection_two_url,
                                       {'data': {'id': self.collection_two._id, 'type': 'node_links'}},
                                       auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_pointers_no_type(self):
        payload = {'data': [
            {'id': self.collection_two_pointer._id},
            {'id': self.collection_two_pointer_two._id}
        ]}
        res = self.app.delete_json_api(self.collection_two_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], "/data/type")

    def test_bulk_delete_pointers_incorrect_type(self):
        payload = {'data': [
            {'id': self.collection_two_pointer._id, 'type': 'Incorrect type.'},
            {'id': self.collection_two_pointer_two._id, 'type': 'Incorrect type.'}
        ]}
        res = self.app.delete_json_api(self.collection_two_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_pointers_no_id(self):
        payload = {'data': [
            {'type': 'node_links'},
            {'type': 'node_links'}
        ]}
        res = self.app.delete_json_api(self.collection_two_url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], "/data/id")

    def test_bulk_delete_pointers_no_data(self):
        res = self.app.delete_json_api(self.collection_two_url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must contain array of resource identifier objects.')

    def test_bulk_delete_pointers_payload_is_empty_dict(self):
        res = self.app.delete_json_api(self.collection_two_url, {}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')

    def test_bulk_deletes_collection_node_pointers_logged_out(self):
        res = self.app.delete_json_api(self.collection_two_url, self.collection_two_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_bulk_deletes_collection_node_pointers_fails_if_bad_auth(self):
        node_count_before = len(self.collection_two.nodes_pointer)
        res = self.app.delete_json_api(self.collection_two_url, self.collection_two_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])
        self.collection_two.reload()
        assert_equal(node_count_before, len(self.collection_two.nodes_pointer))

    def test_bulk_deletes_collection_node_pointers_succeeds_as_owner(self):
        node_count_before = len(self.collection_two.nodes_pointer)
        res = self.app.delete_json_api(self.collection_two_url, self.collection_two_payload, auth=self.user.auth, bulk=True)
        self.collection_two.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 2, len(self.collection_two.nodes_pointer))
        self.collection_two.reload()

    def test_return_bulk_deleted_collection_node_pointer(self):
        res = self.app.delete_json_api(self.collection_two_url, self.collection_two_payload, auth=self.user.auth, bulk=True)
        self.collection_two.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        pointer_url = '/{}collections/{}/node_links/{}/'.format(API_BASE, self.collection_two._id, self.collection_two_pointer._id)

        #check that deleted pointer can not be returned
        res = self.app.get(pointer_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_bulk_delete_link_that_is_not_linked_to_correct_node(self):
        project = ProjectFactory(creator=self.user)
        # The node link belongs to a different project
        res = self.app.delete_json_api(
            self.collection_url, self.collection_two_payload,
            auth=self.user.auth,
            expect_errors=True,
            bulk=True
        )
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Node link does not belong to the requested node.')

class TestCollectionRelationshipNodeLinks(ApiTestCase):

    def setUp(self):
        super(TestCollectionRelationshipNodeLinks, self).setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.auth = Auth(self.user)
        self.collection = CollectionFactory(creator=self.user)
        self.admin_node = NodeFactory(creator=self.user)
        self.contributor_node = NodeFactory(creator=self.user2)
        self.contributor_node.add_contributor(self.user, auth=Auth(self.user2))
        self.contributor_node.save()
        self.other_node = NodeFactory()
        self.private_node = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True)
        self.collection.add_pointer(self.private_node, auth=self.auth)
        self.public_collection = CollectionFactory(is_public=True, creator=self.user2)
        self.public_collection.add_pointer(self.private_node, auth=Auth(self.user2))
        self.public_collection.add_pointer(self.public_node, auth=Auth(self.user2))
        self.url = '/{}collections/{}/relationships/linked_nodes/'.format(API_BASE, self.collection._id)
        self.public_url = '/{}collections/{}/relationships/linked_nodes/'.format(API_BASE, self.public_collection._id)

    def payload(self, node_ids=None):
        node_ids = node_ids or [self.admin_node._id]
        env_linked_nodes = [{"type": "linked_nodes", "id": node_id} for node_id in node_ids]
        return {"data": env_linked_nodes}

    def test_get_relationship_linked_nodes(self):
        res = self.app.get(
            self.url, auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        assert_in(self.collection.linked_nodes_self_url, res.json['links']['self'])
        assert_in(self.collection.linked_nodes_related_url, res.json['links']['html'])
        assert_equal(res.json['data'][0]['id'], self.private_node._id)

    def test_get_public_relationship_linked_nodes_logged_out(self):
        res = self.app.get(self.public_url)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_node._id)

    def test_get_public_relationship_linked_nodes_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

    def test_get_private_relationship_linked_nodes_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_post_contributing_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_public_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.public_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.public_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_private_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_mixed_nodes(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_not_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_node_already_linked(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

    def test_put_contributing_node(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.contributor_node._id, ids)
        assert_not_in(self.private_node._id, ids)

    def test_put_private_node(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_put_mixed_nodes(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_not_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_delete_with_put_empty_array(self):
        self.collection.add_pointer(self.admin_node, auth=self.auth)
        payload = self.payload()
        payload['data'].pop()
        res = self.app.put_json_api(
            self.url, payload,
            auth=self.user.auth
        )
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'], payload['data'])

    def test_delete_one(self):
        self.collection.add_pointer(self.admin_node, auth=self.auth)
        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url, auth=self.user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.admin_node._id, ids)
        assert_not_in(self.private_node._id, ids)

    def test_delete_multiple(self):
        self.collection.add_pointer(self.admin_node, auth=self.auth)
        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id, self.admin_node._id]),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_delete_not_present(self):
        number_of_links = len(self.collection.nodes)
        res = self.app.delete_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(
            self.url, auth=self.user.auth
        )
        assert_equal(len(res.json['data']), number_of_links)

    def test_access_other_collection(self):
        other_collection = CollectionFactory(creator=self.user2)
        url = '/{}collections/{}/relationships/linked_nodes/'.format(API_BASE, other_collection._id)
        res = self.app.get(
            url, auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_node_doesnt_exist(self):
        res = self.app.post_json_api(
            self.url, self.payload(['aquarela']),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 404)

    def test_type_mistyped(self):
        res = self.app.post_json_api(
            self.url,
            {
                'data': [{'type': 'not_linked_nodes', 'id': self.contributor_node._id}]
            },
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 409)

    def test_creates_public_linked_node_relationship_logged_out(self):
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_creates_public_linked_node_relationship_logged_in(self):
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_creates_private_linked_node_relationship_logged_out(self):
        res = self.app.post_json_api(
                self.url, self.payload([self.other_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_put_public_nodes_relationships_logged_out(self):
        res = self.app.put_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_put_public_nodes_relationships_logged_in(self):
        res = self.app.put_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_delete_public_nodes_relationships_logged_out(self):
        res = self.app.delete_json_api(
            self.public_url, self.payload([self.public_node._id]),
            expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_delete_public_nodes_relationships_logged_in(self):
        res = self.app.delete_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_node_links_and_relationship_represent_same_nodes(self):
        self.collection.add_pointer(self.admin_node, auth=self.auth)
        self.collection.add_pointer(self.contributor_node, auth=self.auth)
        res_relationship = self.app.get(
            self.url, auth=self.user.auth
        )
        res_node_links = self.app.get(
            '/{}collections/{}/node_links/'.format(API_BASE, self.collection._id),
            auth=self.user.auth
        )
        node_links_id = [data['embeds']['target_node']['data']['id'] for data in res_node_links.json['data']]
        relationship_id = [data['id'] for data in res_relationship.json['data']]

        assert_equal(set(node_links_id), set(relationship_id))

    def test_attempt_to_add_collection_to_collection(self):
        other_collection = CollectionFactory(creator=self.user)
        res = self.app.post_json_api(
            self.url, self.payload([other_collection._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 404)


class TestCollectionLinkedNodes(ApiTestCase):
    def setUp(self):
        super(TestCollectionLinkedNodes, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.collection = CollectionFactory(creator=self.user)
        self.linked_node = NodeFactory(creator=self.user)
        self.linked_node2 = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True, creator=self.user)
        self.collection.add_pointer(self.linked_node, auth=self.auth)
        self.collection.add_pointer(self.linked_node2, auth=self.auth)
        self.collection.add_pointer(self.public_node, auth=self.auth)
        self.collection.save()
        self.url = '/{}collections/{}/linked_nodes/'.format(API_BASE, self.collection._id)
        self.node_ids = [pointer.node._id for pointer in self.collection.nodes_pointer]

    def test_linked_nodes_returns_everything(self):
        res = self.app.get(self.url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids))

        for node_id in self.node_ids:
            assert_in(node_id, nodes_returned)

    def test_linked_nodes_only_return_viewable_nodes(self):
        user = AuthUserFactory()
        collection = CollectionFactory(creator=user)
        self.linked_node.add_contributor(user, auth=self.auth, save=True)
        self.linked_node2.add_contributor(user, auth=self.auth, save=True)
        self.public_node.add_contributor(user, auth=self.auth, save=True)
        collection.add_pointer(self.linked_node, auth=Auth(user))
        collection.add_pointer(self.linked_node2, auth=Auth(user))
        collection.add_pointer(self.public_node, auth=Auth(user))
        collection.save()

        res = self.app.get(
            '/{}collections/{}/linked_nodes/'.format(API_BASE, collection._id),
            auth=user.auth
        )

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids))

        for node_id in self.node_ids:
            assert_in(node_id, nodes_returned)

        self.linked_node2.remove_contributor(user, auth=self.auth)
        self.public_node.remove_contributor(user, auth=self.auth)

        res = self.app.get(
            '/{}collections/{}/linked_nodes/'.format(API_BASE, collection._id),
            auth=user.auth
        )
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids) - 1)

        assert_in(self.linked_node._id, nodes_returned)
        assert_in(self.public_node._id, nodes_returned)
        assert_not_in(self.linked_node2._id, nodes_returned)

    def test_linked_nodes_doesnt_return_deleted_nodes(self):
        self.linked_node.is_deleted = True
        self.linked_node.save()
        res = self.app.get(self.url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids) - 1)

        assert_not_in(self.linked_node._id, nodes_returned)
        assert_in(self.linked_node2._id, nodes_returned)
        assert_in(self.public_node._id, nodes_returned)

    def test_attempt_to_return_linked_nodes_logged_out(self):
        res = self.app.get(
            self.url, auth=None,
            expect_errors=True
        )

        assert_equal(res.status_code, 401)
