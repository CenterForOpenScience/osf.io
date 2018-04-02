import pytest
from urlparse import urlparse

from django.utils.timezone import now

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    CollectionFactory,
    NodeFactory,
    RegistrationFactory,
    ProjectFactory,
    AuthUserFactory,
)
from osf.models import Collection
from osf.utils.sanitize import strip_html
from tests.utils import assert_items_equal
from website.project.signals import contributor_removed
from api_tests.utils import disconnected_from_listeners
from website.views import find_bookmark_collection


url_collection_list = '/{}collections/'.format(API_BASE)


@pytest.fixture()
def user_one():
    return AuthUserFactory()


@pytest.mark.django_db
class TestCollectionList:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection(self, user_one):
        return CollectionFactory(creator=user_one)

    @pytest.fixture()
    def collection_deleted(self, user_one):
        return CollectionFactory(creator=user_one, deleted=now())

    def test_user_get_own_collections(
            self, app, user_one, user_two,
            collection_deleted, collection
    ):

        # test_user_one_gets_user_one_collections
        res = app.get(url_collection_list, auth=user_one.auth)
        ids = [each['id'] for each in res.json['data']]
        assert collection_deleted._id not in ids
        assert collection._id in ids

        # test_user_two_gets_nothing
        res = app.get(url_collection_list, auth=user_two.auth)
        ids = [each['id'] for each in res.json['data']]
        assert collection_deleted._id not in ids
        assert collection._id not in ids

        # test_unauthorized_gets_nothing
        res = app.get(url_collection_list)
        ids = [each['id'] for each in res.json['data']]
        assert collection_deleted._id not in ids
        assert collection._id not in ids


@pytest.mark.django_db
class TestCollectionCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def title_collection(self):
        return 'Cool Collection'

    @pytest.fixture()
    def data_collection(self, title_collection):
        return {
            'data': {
                'type': 'collections',
                'attributes':
                    {
                        'title': title_collection,
                    }
            }
        }

    @pytest.fixture()
    def bookmark_user_one(self, user_one):
        bookmark_user_one = find_bookmark_collection(user_one)
        bookmark_user_one.deleted = now()
        bookmark_user_one.save()
        return bookmark_user_one

    @pytest.fixture()
    def bookmark_user_two(self, user_two):
        bookmark_user_two = find_bookmark_collection(user_two)
        bookmark_user_two.deleted = now()
        bookmark_user_two.save()
        return bookmark_user_two

    def test_create_collection_fails(
            self, app, data_collection,
            user_one, title_collection
    ):

        # test_collection_create_invalid_data
        res = app.post_json_api(
            url_collection_list, 'Incorrect data',
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Malformed request.'

        res = app.post_json_api(
            url_collection_list, ['Incorrect data'],
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Malformed request.'

        # test_creates_collection_logged_out
        res = app.post_json_api(
            url_collection_list, data_collection,
            expect_errors=True
        )
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_creates_collection_logged_in
        res = app.post_json_api(
            url_collection_list, data_collection,
            auth=user_one.auth
        )
        assert res.status_code == 201
        pid = res.json['data']['id']
        assert res.json['data']['attributes']['title'] == title_collection
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['type'] == 'collections'
        res = app.get(
            '{}?filter[title]={}'.format(
                url_collection_list,
                title_collection
            ), auth=user_one.auth
        )
        ids = [each['id'] for each in res.json['data']]
        assert pid in ids
        collection = Collection.load(pid)
        assert collection.title == title_collection

        # test_creates_project_no_type
        collection = {
            'data': {
                'attributes': {
                    'title': title_collection,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list, collection,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # test_creates_project_incorrect_type
        collection = {
            'data': {
                'attributes': {
                    'title': title_collection,
                },
                'type': 'Wrong type.'
            }
        }
        res = app.post_json_api(
            url_collection_list, collection,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "collections", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

        # test_creates_collection_properties_not_nested
        project = {
            'data': {
                'title': title_collection,
                'type': 'collections'
            }
        }
        res = app.post_json_api(
            url_collection_list, project,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/attributes.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

        # test_create_bookmark_collection_with_no_title
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'bookmarks': True,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list, collection,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400

        # test_create_project_invalid_title
        project = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'A' * 201,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list, project,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Title cannot exceed 200 characters.'

    def test_create_bookmark_collection(
            self, app, bookmark_user_one,
            data_collection, user_one
    ):
        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list,
            collection,
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['title'] == 'Bookmarks'
        assert res.json['data']['attributes']['bookmarks']

    def test_cannot_create_multiple_bookmark_collection(
            self, app, bookmark_user_one, data_collection, user_one, title_collection):

        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list,
            collection,
            auth=user_one.auth)
        assert res.status_code == 201
        res = app.post_json_api(
            url_collection_list,
            collection,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Each user cannot have more than one Bookmark collection.'

    def test_create_bookmark_collection_with_wrong_title(
            self, app, bookmark_user_one, data_collection, user_one):

        collection = {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': 'Not Bookmarks',
                    'bookmarks': True,
                }
            }
        }
        res = app.post_json_api(
            url_collection_list,
            collection,
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['title'] == 'Bookmarks'
        assert res.json['data']['attributes']['bookmarks']

    def test_create_collection_creates_collection_and_sanitizes_html(
            self, app, data_collection, user_one):
        title = '<em>Cool</em> <script>alert("even cooler")</script> <strong>Project</strong>'

        res = app.post_json_api(url_collection_list, {
            'data': {
                'attributes': {
                    'title': title,
                },
                'type': 'collections'
            }
        }, auth=user_one.auth)
        collection_id = res.json['data']['id']
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'

        collection = Collection.load(collection_id)
        assert collection.title == strip_html(title)


@pytest.mark.django_db
class TestCollectionFiltering:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection_one(self, user_one):
        return CollectionFactory(title='Collection One', creator=user_one)

    @pytest.fixture()
    def collection_two(self, user_one):
        return CollectionFactory(title='Collection Two', creator=user_one)

    @pytest.fixture()
    def collection_three(self, user_one):
        return CollectionFactory(title='Three', creator=user_one)

    def test_collection_filtering(
            self, app, user_one, user_two,
            collection_one, collection_two, collection_three):

        # test_get_all_projects_with_no_filter_logged_in
        res = app.get(url_collection_list, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert collection_one._id in ids
        assert collection_two._id in ids
        assert collection_three._id in ids

        # test_get_no_collections_with_no_filter_not_logged_in
        res = app.get(url_collection_list)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert collection_one._id not in ids
        assert collection_two._id not in ids
        assert collection_three._id not in ids

        # test_get_no_collections_with_no_filter_logged_in_as_wrong_user
        res = app.get(url_collection_list, auth=user_two.auth)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert collection_one._id not in ids
        assert collection_two._id not in ids
        assert collection_three._id not in ids

        # test_get_one_collection_with_exact_filter_logged_in
        url = '/{}collections/?filter[title]=Collection%20One'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert collection_one._id in ids
        assert collection_two._id not in ids
        assert collection_three._id not in ids

        # test_get_one_collection_with_exact_filter_not_logged_in
        url = '/{}collections/?filter[title]=Collection%20One'.format(API_BASE)

        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert collection_one._id not in ids
        assert collection_two._id not in ids
        assert collection_three._id not in ids

        # test_get_some_collections_with_substring_logged_in
        url = '/{}collections/?filter[title]=Two'.format(API_BASE)

        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert collection_one._id not in ids
        assert collection_two._id in ids
        assert collection_three._id not in ids

        # test_get_no_projects_with_substring_not_logged_in
        url = '/{}collections/?filter[title]=Two'.format(API_BASE)

        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert collection_one._id not in ids
        assert collection_two._id not in ids
        assert collection_three._id not in ids

        # test_incorrect_filtering_field_logged_in
        url = '/{}collections/?filter[notafield]=bogus'.format(API_BASE)

        res = app.get(url, expect_errors=True)
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == '\'notafield\' is not a valid field for this endpoint.'
        assert errors[0]['source'] == {'parameter': 'filter'}


@pytest.mark.django_db
class TestCollectionDetail:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection(self, user_one):
        return CollectionFactory(title='Test collection', creator=user_one)

    @pytest.fixture()
    def url_collection_detail(self, collection):
        return '/{}collections/{}/'.format(API_BASE, collection._id)

    def test_collection_detail_returns(
            self, app, url_collection_detail,
            user_one, user_two, collection
    ):

        # test_do_not_return_collection_details_logged_out
        res = app.get(url_collection_detail, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_return_collection_details_logged_in
        res = app.get(url_collection_detail, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == collection.title
        node_links_url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = url_collection_detail + 'node_links/'
        assert urlparse(node_links_url).path == expected_url

        # test_do_not_return_collection_details_logged_in_non_contributor
        res = app.get(
            url_collection_detail,
            auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_requesting_node_returns_error
        node = NodeFactory(creator=user_one)
        res = app.get(
            '/{}collections/{}/'.format(API_BASE, node._id),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 404


@pytest.mark.django_db
class CollectionCRUDTestCase:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def title_collection(self):
        return 'Cool Collection'

    @pytest.fixture()
    def new_title_collection(self):
        return 'Super Cool Collection'

    @pytest.fixture()
    def collection(self, title_collection, user_one):
        return CollectionFactory(title=title_collection, creator=user_one)

    @pytest.fixture()
    def url_collection_detail(self, collection):
        return '/{}collections/{}/'.format(API_BASE, collection._id)

    @pytest.fixture()
    def url_fake_collection_detail(self, collection):
        return '/{}collections/{}/'.format(API_BASE, '12345')

    @pytest.fixture()
    def payload_collection(self, collection):
        def make_collection_payload(attributes):
            return {
                'data': {
                    'id': collection._id,
                    'type': 'collections',
                    'attributes': attributes,
                }
            }
        return make_collection_payload


@pytest.mark.django_db
class TestCollectionUpdate(CollectionCRUDTestCase):

    def test_update_collection_logged_in(
            self, app, url_collection_detail,
            collection, new_title_collection, user_one
    ):
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == new_title_collection
        collection.reload()
        assert collection.title == new_title_collection

    def test_partial_update_collection_logged_in(
            self, app, url_collection_detail,
            collection, new_title_collection, user_one
    ):
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == new_title_collection
        collection.reload()
        assert collection.title == new_title_collection

    def test_update_collection_sanitizes_html_properly(
            self, app, url_collection_detail, collection, user_one):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong><script>alert("even cooler")</script> Cool Project'
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title,
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == strip_html(new_title)
        collection.reload()
        assert collection.title == strip_html(new_title)

    def test_partial_update_collection_updates_project_correctly_and_sanitizes_html(
            self, app, url_collection_detail, collection, user_one):
        new_title = 'An <script>alert("even cooler")</script> project'
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        collection.reload()
        assert collection.title == strip_html(new_title)

    def test_update_collection_should_fail(
            self, app, url_collection_detail, user_one,
            user_two, new_title_collection, collection
    ):

        # test_node_update_invalid_data
        res = app.put_json_api(
            url_collection_detail, 'Incorrect data',
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Malformed request.'

        res = app.patch_json_api(
            url_collection_detail, ['Incorrect data'],
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Malformed request.'

        # test_update_collection_properties_not_nested
        res = app.put_json_api(url_collection_detail, {
            'id': collection._id,
            'type': 'collections',
            'title': new_title_collection,
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        # test_update_invalid_id
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': '12345',
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

        # test_update_invalid_type
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collection',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

        # test_update_no_id
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

        # test_update_no_type
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # test_cannot_update_collection_logged_out
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_cannot_update_collection_logged_in_but_unauthorized
        res = app.put_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_partial_update_collection_logged_in_but_unauthorized
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'attributes': {
                    'title': new_title_collection},
                'id': collection._id,
                'type': 'nodes',
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_partial_update_invalid_id
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': '12345',
                'type': 'collections',
                'attributes': {
                        'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

        # test_partial_update_invalid_type
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'collection',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

        # test_partial_update_no_id
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'type': 'collections',
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

        # test_partial_update_no_type
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'attributes': {
                    'title': new_title_collection,
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # Nothing will be updated here
        # test_partial_update_collection_properties_not_nested
        res = app.patch_json_api(url_collection_detail, {
            'data': {
                'id': collection._id,
                'type': 'nodes',
                'title': new_title_collection,
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

        # test_update_collection_invalid_title
        project = {
            'data': {
                'type': 'collections',
                'id': collection._id,
                'attributes': {
                    'title': 'A' * 201,
                    'category': 'project',
                }
            }
        }
        res = app.put_json_api(
            url_collection_detail, project,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Title cannot exceed 200 characters.'


@pytest.mark.django_db
class TestCollectionDelete(CollectionCRUDTestCase):

    def test_do_not_delete_collection_unauthenticated(
            self, app, url_collection_detail):
        res = app.delete(url_collection_detail, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    def test_do_not_return_deleted_collection(
            self, app, collection, url_collection_detail):
        collection.deleted = now()
        collection.save()
        res = app.get(url_collection_detail, expect_errors=True)
        assert res.status_code == 410
        assert 'detail' in res.json['errors'][0]

    def test_cannot_delete_invalid_collection(
            self, app, url_fake_collection_detail, user_one):
        res = app.delete(
            url_fake_collection_detail,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

    def test_do_not_delete_collection_unauthorized(
            self, app, url_collection_detail, user_two, collection):
        res = app.delete_json_api(
            url_collection_detail,
            auth=user_two.auth,
            expect_errors=True)
        collection.reload()
        assert res.status_code == 403
        assert not collection.deleted
        assert 'detail' in res.json['errors'][0]

    def test_delete_collection_authorized(
            self, app, url_collection_detail,
            user_one, collection
    ):
        res = app.delete_json_api(
            url_collection_detail,
            auth=user_one.auth, expect_errors=True
        )
        collection.reload()
        assert res.status_code == 204
        assert collection.deleted


@pytest.mark.django_db
class TestCollectionNodeLinksList:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_private(self, user_one):
        return ProjectFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def project_public(self, user_two):
        return ProjectFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def registration_private(self, user_one):
        return RegistrationFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def registration_public(self, user_two):
        return RegistrationFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def collection(
            self, user_one, project_private, project_public,
            registration_private, registration_public
    ):
        collection = CollectionFactory(creator=user_one)
        collection.collect_object(project_private, user_one)
        collection.collect_object(project_public, user_one)
        collection.collect_object(registration_private, user_one)
        collection.collect_object(registration_public, user_one)
        return collection

    @pytest.fixture()
    def url_collection_nodelinks(self, collection):
        return '/{}collections/{}/node_links/'.format(API_BASE, collection._id)

    def test_collection_nodelinks_list_returns(
            self, app, url_collection_nodelinks, collection,
            user_one, user_two, project_public, project_private,
            registration_public, registration_private):

        # test_do_not_return_node_pointers_logged_out
        res = app.get(url_collection_nodelinks, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_return_node_pointers_logged_in
        res = app.get(url_collection_nodelinks, auth=user_one.auth)
        res_json = res.json['data']
        assert len(res_json) == 4
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

        first_embedded = res_json[0]['embeds']['target_node']['data']['id']
        second_embedded = res_json[1]['embeds']['target_node']['data']['id']
        # node_links end point does not handle registrations correctly
        third_embedded = res_json[2]['embeds']['target_node']['errors'][0]['detail']
        fourth_embedded = res_json[3]['embeds']['target_node']['errors'][0]['detail']
        assert_items_equal(
            [first_embedded, second_embedded, third_embedded, fourth_embedded],
            [project_private._id, project_public._id, 'Not found.', 'Not found.'])

        # test_return_private_node_pointers_logged_in_non_contributor
        res = app.get(
            url_collection_nodelinks,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_deleted_links_not_returned
        res = app.get(url_collection_nodelinks, auth=user_one.auth)
        res_json = res.json['data']
        original_length = len(res_json)

        project_public.is_deleted = True
        project_public.save()

        res = app.get(url_collection_nodelinks, auth=user_one.auth)
        res_json = res.json['data']
        assert len(res_json) == original_length - 1


def make_post_payload(
        target_node_id,
        outer_type='node_links',
        inner_type='nodes'):
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


@pytest.mark.django_db
class TestCollectionNodeLinkCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection_one(self, user_one):
        return CollectionFactory(creator=user_one)

    @pytest.fixture()
    def collection_two(self, user_two):
        return CollectionFactory(creator=user_two)

    @pytest.fixture()
    def project_private_user_one(self, user_one):
        return ProjectFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def project_public_user_one(self, user_one):
        return ProjectFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def registration_private_user_one(self, user_one):
        return RegistrationFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def registration_public_user_one(self, user_one):
        return RegistrationFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def project_private_user_two(self, user_two):
        return ProjectFactory(is_public=False, creator=user_two)

    @pytest.fixture()
    def project_public_user_two(self, user_two):
        return ProjectFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def registration_private_user_two(self, user_two):
        return RegistrationFactory(is_public=False, creator=user_two)

    @pytest.fixture()
    def registration_public_user_two(self, user_two):
        return RegistrationFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def url_collection_nodelinks(self, collection_one):
        return '/{}collections/{}/node_links/'.format(
            API_BASE, collection_one._id)

    @pytest.fixture()
    def id_fake_node(self):
        return 'fakeident'

    @pytest.fixture()
    def url_fake_collection_nodelinks(self, id_fake_node):
        return '/{}collections/{}/node_links/'.format(API_BASE, id_fake_node)

    def test_creates_node_link_to_public_project_logged_in(
            self, app, url_collection_nodelinks,
            project_public_user_one, collection_one, user_one
    ):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(project_public_user_one._id),
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert embedded_node_id == project_public_user_one._id

    def test_creates_node_link_to_public_registration_logged_in(
            self, app, collection_one, url_collection_nodelinks,
            registration_public_user_one, user_one
    ):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(registration_public_user_one._id),
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        # node_links end point does not handle registrations correctly
        embedded_node_id = res_json['embeds']['target_node']['errors'][0]['detail']
        assert embedded_node_id == 'Not found.'

    def test_creates_node_link_to_private_project_logged_in(
            self, app, collection_one, url_collection_nodelinks,
            user_one, project_private_user_one):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(project_private_user_one._id),
            auth=user_one.auth)
        assert res.status_code == 201
        res_json = res.json['data']
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert embedded_node_id == project_private_user_one._id

    def test_creates_node_link_to_private_registration_logged_in(
            self, app, url_collection_nodelinks, collection_one,
            registration_private_user_one, user_one):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(registration_private_user_one._id),
            auth=user_one.auth)
        assert res.status_code == 201
        res_json = res.json['data']
        # node_links end point does not handle registrations correctly
        embedded_node_id = res_json['embeds']['target_node']['errors'][0]['detail']
        assert embedded_node_id == 'Not found.'

    def test_create_node_link_to_non_contributing_node(
            self, app, collection_one, url_collection_nodelinks,
            project_public_user_two, user_one):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(project_public_user_two._id),
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert embedded_node_id == project_public_user_two._id

    def test_create_node_link_to_non_contributing_registration(
            self, app, collection_one, url_collection_nodelinks,
            registration_public_user_two, user_one):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(registration_public_user_two._id),
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        # node_links end point does not handle registrations correctly
        embedded_node_id = res_json['embeds']['target_node']['errors'][0]['detail']
        assert embedded_node_id == 'Not found.'

    def test_create_node_pointer_already_connected(
            self, app, collection_one, url_collection_nodelinks,
            project_private_user_one, user_one):
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(project_private_user_one._id),
            auth=user_one.auth)
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded_node_id = res_json['embeds']['target_node']['data']['id']
        assert embedded_node_id == project_private_user_one._id

        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(project_private_user_one._id),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 400
        error = res.json['errors'][0]
        assert 'detail' in error
        assert 'Target Node \'{}\' already pointed to by \'{}\'.'.format(
            project_private_user_one._id, collection_one._id) == error['detail']
        assert 'source' in error
        assert 'pointer' in error['source']
        assert '/data/relationships/node_links/data/id' == error['source']['pointer']

    def test_non_mutational_collection_nodelink_create_tests(
            self, app, user_one, user_two, collection_one,
            url_collection_nodelinks,
            url_fake_collection_nodelinks,
            id_fake_node, project_public_user_one,
            project_private_user_one,
            project_private_user_two,
            registration_public_user_two,
    ):

        # test_create_node_pointer_no_type
        payload = make_post_payload(
            project_public_user_one._id, outer_type=None)
        res = app.post_json_api(
            url_collection_nodelinks,
            payload,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # test_create_node_pointer_incorrect_type
        payload = make_post_payload(
            project_public_user_one._id,
            outer_type='wrong_type')
        res = app.post_json_api(
            url_collection_nodelinks,
            payload,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "node_links", but you set the json body\'s type field to "wrong_type". You probably need to change the type field to match the resource\'s type.'

        # test_does_not_create_link_when_payload_not_nested
        payload = {
            'data': {
                'type': 'node_links',
                'target_node_id': project_private_user_one._id}}
        res = app.post_json_api(
            url_collection_nodelinks,
            payload,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'

        # test_does_not_create_node_link_logged_out
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(
                project_private_user_one._id),
            expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_does_not_create_node_link_unauthorized
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(
                project_private_user_two._id),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_does_not_create_registration_link_unauthorized
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(
                registration_public_user_two._id),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_create_node_link_to_fake_node
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(id_fake_node),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'detail' in res.json['errors'][0]
        assert 'source' in res.json['errors'][0]

        # test_fake_collection_pointing_to_valid_node
        res = app.post_json_api(
            url_fake_collection_nodelinks,
            make_post_payload(
                project_private_user_one._id),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        res = app.post_json_api(
            url_fake_collection_nodelinks,
            make_post_payload(
                project_private_user_one._id),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        # test_create_collection_node_pointer_to_itself
        res = app.post_json_api(
            url_collection_nodelinks,
            make_post_payload(
                collection_one._id),
            auth=user_one.auth,
            expect_errors=True)
        res_json = res.json
        assert res.status_code == 400
        error = res_json['errors'][0]
        assert 'detail' in error
        assert 'Target Node \'{}\' not found.'.format(
            collection_one._id) == error['detail']
        assert 'source' in error
        assert 'pointer' in error['source']
        assert '/data/relationships/node_links/data/id' == error['source']['pointer']


@pytest.mark.django_db
class TestCollectionNodeLinkDetail:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection(self, user_one):
        return CollectionFactory(creator=user_one)

    @pytest.fixture()
    def project_private(self, user_one):
        return ProjectFactory(creator=user_one, is_public=False)

    @pytest.fixture()
    def project_public(self, user_one):
        return ProjectFactory(creator=user_one, is_public=False)

    @pytest.fixture()
    def registration_private(self, user_one):
        return RegistrationFactory(creator=user_one, is_public=False)

    @pytest.fixture()
    def registration_public(self, user_one):
        return RegistrationFactory(creator=user_one, is_public=False)

    @pytest.fixture()
    def node_link_private(self, user_one, collection, project_private):
        return collection.collect_object(
            project_private, user_one).guid.referent

    @pytest.fixture()
    def node_link_public(self, user_one, collection, project_public):
        return collection.collect_object(
            project_public, user_one).guid.referent

    @pytest.fixture()
    def registration_link_private(
            self, user_one, registration_private,
            collection
    ):
        return collection.collect_object(
            registration_private,
            user_one
        ).guid.referent

    @pytest.fixture()
    def registration_link_public(
            self, user_one, registration_public,
            collection
    ):
        return collection.collect_object(
            registration_public, user_one).guid.referent

    @pytest.fixture()
    def url_node_link_private(self, collection, node_link_private):
        return '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection._id, node_link_private._id)

    @pytest.fixture()
    def url_node_link_public(self, collection, node_link_public):
        return '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection._id, node_link_public._id
        )

    @pytest.fixture()
    def url_registration_link_private(
            self, collection, registration_link_private):
        return '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection._id, registration_link_private._id
        )

    @pytest.fixture()
    def url_registration_link_public(
            self, collection, registration_link_public):
        return '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection._id, registration_link_public._id
        )

    def test_returns_public_node_pointer_detail_authorized(
            self, app, user_one, url_node_link_public, project_public):
        res = app.get(url_node_link_public, auth=user_one.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == project_public._id

    def test_returns_public_registration_pointer_detail_authorized(
            self, app, user_one, url_registration_link_public):
        res = app.get(url_registration_link_public, auth=user_one.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        # node_links end point does not handle registrations correctly
        embedded = res_json['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

    def test_returns_private_node_link_detail_authorized(
            self, app, user_one, url_node_link_private, project_private):
        res = app.get(url_node_link_private, auth=user_one.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        embedded = res_json['embeds']['target_node']['data']['id']
        assert embedded == project_private._id

    def test_returns_private_registration_link_detail_authorized(
            self, app, url_registration_link_private, user_one):
        res = app.get(url_registration_link_private, auth=user_one.auth)
        res_json = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        # node_links end point does not handle registrations correctly
        embedded = res_json['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

    def test_self_link_points_to_node_link_detail_url(
            self, app, url_node_link_private, user_one):
        res = app.get(url_node_link_private, auth=user_one.auth)
        assert res.status_code == 200
        url = res.json['data']['links']['self']
        assert url_node_link_private in url

    def test_delete_node_link_no_permissions_for_target_node(
            self, app, user_one, user_two, collection):
        pointed_project = ProjectFactory(creator=user_two)
        pointer = collection.collect_object(
            pointed_project, user_one)
        assert collection.guid_links.filter(_id=pointed_project._id).exists()
        url = '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection._id, pointer._id)
        res = app.delete_json_api(url, auth=user_one.auth)
        assert res.status_code == 204
        assert not collection.deleted
        assert not collection.guid_links.filter(_id=pointed_project._id).exists()

    def test_delete_public_node_pointer_authorized(
            self, app, user_one, url_node_link_public, collection):
        node_count_before = collection.guid_links.count()
        res = app.delete(url_node_link_public, auth=user_one.auth)
        assert res.status_code == 204
        assert node_count_before - 1 == collection.guid_links.count()

    def test_delete_public_registration_pointer_authorized(
            self, app, user_one, collection, url_registration_link_public):
        node_count_before = collection.guid_links.count()
        res = app.delete(url_registration_link_public, auth=user_one.auth)
        collection.reload()
        assert res.status_code == 204
        assert node_count_before - 1 == collection.guid_links.count()

    def test_delete_private_node_link_authorized(
            self, app, url_node_link_private, user_one, collection):
        node_count_before = collection.guid_links.count()
        res = app.delete(url_node_link_private, auth=user_one.auth)
        assert res.status_code == 204
        assert node_count_before - 1 == collection.guid_links.count()

    def test_delete_private_registration_link_authorized(
            self, app, user_one, url_registration_link_private, collection):
        node_count_before = collection.guid_links.count()
        res = app.delete(url_registration_link_private, auth=user_one.auth)
        assert res.status_code == 204
        assert node_count_before - 1 == collection.guid_links.count()

    def test_can_not_return_deleted_collection_public_node_pointer(
            self, app, user_one, url_node_link_public, collection):
        res = app.delete(url_node_link_public, auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(
            url_node_link_public,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_can_not_return_deleted_collection_public_registration_pointer(
            self, app, url_registration_link_public, user_one, collection):
        res = app.delete(url_registration_link_public, auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(
            url_registration_link_public,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_return_deleted_private_node_pointer(
            self, app, collection, url_node_link_private,
            user_one, project_private
    ):
        res = app.delete(url_node_link_private, auth=user_one.auth)
        project_private.reload()
        assert res.status_code == 204

        res = app.get(
            url_node_link_private,
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 404

    def test_return_deleted_private_registration_pointer(
            self, app, collection, url_registration_link_private,
            user_one, project_private
    ):
        res = app.delete(url_registration_link_private, auth=user_one.auth)
        project_private.reload()
        assert res.status_code == 204

        res = app.get(
            url_registration_link_private,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_non_mutational_collection_nodelink_detail_tests(
            self, app, collection, user_one, user_two,
            url_node_link_public, node_link_private,
            url_registration_link_public,
            url_node_link_private,
            url_registration_link_private):

        # test_returns_error_public_node_link_detail_unauthenticated
        res = app.get(url_node_link_public, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_returns_error_public_registration_link_detail_unauthenticated
        res = app.get(url_registration_link_public, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_returns_error_private_node_link_detail_unauthenticated
        res = app.get(url_node_link_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_returns_error_private_registration_link_detail_unauthenticated
        res = app.get(url_registration_link_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_returns_error_private_node_link_detail_unauthorized
        res = app.get(
            url_node_link_private,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_returns_error_private_registration_link_detail_unauthorized
        res = app.get(
            url_registration_link_private,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_can_not_delete_collection_public_node_link_unauthenticated
        res = app.delete(url_node_link_public, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0].keys()

        # test_can_not_delete_collection_public_node_pointer_unauthorized
        node_count_before = collection.guid_links.count()
        res = app.delete(
            url_node_link_public,
            auth=user_two.auth, expect_errors=True
        )
        # This is could arguably be a 405, but we don't need to go crazy with
        # status codes
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]
        collection.reload()
        assert node_count_before == collection.guid_links.count()

        # test_can_not_delete_collection_private_node_link_unauthorized
        res = app.delete(
            url_node_link_private,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_can_not_delete_collection_private_registration_link_unauthorized
        res = app.delete(
            url_registration_link_private,
            auth=user_two.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # Regression test for https://openscience.atlassian.net/browse/OSF-4322
        # test_delete_link_that_is_not_linked_to_correct_node
        collection = CollectionFactory(creator=user_one)
        # The node link belongs to a different project
        res = app.delete(
            '/{}nodes/{}/node_links/{}/'.format(
                API_BASE, collection._id, node_link_private._id
            ),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 404
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Not found.'


@pytest.mark.django_db
class TestReturnDeletedCollection:

    def test_return_deleted_collection(self, app):

        user = AuthUserFactory()
        AuthUserFactory()

        collection_deleted = CollectionFactory(
            deleted=now(), creator=user, title='This collection has been deleted')
        CollectionFactory(
            creator=user, title='A boring collection')

        title_new = 'This deleted node has been edited'
        url_collection_deleted = '/{}collections/{}/'.format(
            API_BASE, collection_deleted._id)

        # test_return_deleted_collection
        res = app.get(url_collection_deleted, expect_errors=True)
        assert res.status_code == 410

        # test_edit_deleted_collection
        res = app.put_json_api(
            url_collection_deleted,
            params={
                'title': title_new},
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410

        # test_delete_deleted_collection
        res = app.delete(
            url_collection_deleted,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410


@pytest.mark.django_db
class TestCollectionBulkCreate:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def url_collections(self):
        return '/{}collections/'.format(API_BASE)

    @pytest.fixture()
    def title_one(self):
        return 'Cool Collection'

    @pytest.fixture()
    def title_two(self):
        return 'Cool Collection, Too'

    @pytest.fixture()
    def collection_one(self, title_one, user_one):
        return {
            'type': 'collections',
            'attributes': {
                    'title': title_one,
            }
        }

    @pytest.fixture()
    def collection_two(self, title_two):
        return {
            'type': 'collections',
            'attributes': {
                    'title': title_two,
            }
        }

    @pytest.fixture()
    def collection_empty(self):
        return {
            'type': 'collections',
            'attributes': {
                    'title': '',
            }
        }

    @pytest.fixture()
    def bookmark_user_one(self, user_one):
        bookmark_user_one = find_bookmark_collection(user_one)
        bookmark_user_one.deleted = now()
        bookmark_user_one.save()
        return bookmark_user_one

    def test_bulk_create_logged_in(
            self, app, bookmark_user_one, url_collections, collection_one,
            collection_two, user_one
    ):
        res = app.post_json_api(
            url_collections, {
                'data': [collection_one, collection_two]
            }, auth=user_one.auth, bulk=True)
        assert res.status_code == 201
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['attributes']['title'] == collection_one['attributes']['title']
        assert res.json['data'][1]['attributes']['title'] == collection_two['attributes']['title']
        assert res.content_type == 'application/vnd.api+json'

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 2
        id_one = res.json['data'][0]['id']
        id_two = res.json['data'][1]['id']

        res = app.delete_json_api(
            url_collections,
            {'data': [
                {'id': id_one, 'type': 'collections'},
                {'id': id_two, 'type': 'collections'}
            ]}, auth=user_one.auth, bulk=True)
        assert res.status_code == 204

    def test_bulk_create_collections_blank_request(
            self, app, url_collections, user_one):
        res = app.post_json_api(
            url_collections, auth=user_one.auth,
            expect_errors=True, bulk=True)
        assert res.status_code == 400

    def test_bulk_create_error_formatting(
            self, app, url_collections, collection_empty,
            user_one
    ):
        res = app.post_json_api(
            url_collections, {'data': [collection_empty, collection_empty]},
            bulk=True, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = res.json['errors']
        assert_items_equal(
            [errors[0]['source'], errors[1]['source']],
            [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal(
            [errors[0]['detail'], errors[1]['detail']],
            ['This field may not be blank.', 'This field may not be blank.'])

    def test_non_mutational_collection_bulk_create_tests(
            self, app, bookmark_user_one, url_collections, collection_one,
            collection_two, collection_empty, user_one, title_one):

        # test_bulk_create_all_or_nothing
        res = app.post_json_api(
            url_collections,
            {'data': [collection_one, collection_empty]},
            bulk=True, auth=user_one.auth, expect_errors=True)

        assert res.status_code == 400

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_logged_out
        res = app.post_json_api(
            url_collections, {
                'data': [collection_one, collection_two]},
            bulk=True, expect_errors=True
        )
        assert res.status_code == 401
        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_limits
        node_create_list = {'data': [collection_one] * 101}
        res = app.post_json_api(
            url_collections, node_create_list,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_no_type
        payload = {'data': [{'attributes': {'title': title_one}}]}
        res = app.post_json_api(
            url_collections, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_incorrect_type
        payload = {
            'data': [
                collection_one, {
                    'type': 'Incorrect type.',
                    'attributes': {'title': title_one}}
            ]
        }
        res = app.post_json_api(
            url_collections, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 409

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_no_attributes
        payload = {'data': [collection_one, {'type': 'collections', }]}
        res = app.post_json_api(
            url_collections, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_bulk_create_no_title
        payload = {
            'data': [
                collection_one, {
                    'type': 'collections',
                    'attributes': {}}
            ]
        }
        res = app.post_json_api(
            url_collections, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/attributes/title'

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0

        # test_ugly_payload
        payload = 'sdf;jlasfd'
        res = app.post_json_api(
            url_collections, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400

        res = app.get(url_collections, auth=user_one.auth)
        assert len(res.json['data']) == 0


@pytest.mark.django_db
class TestCollectionBulkUpdate:

    @pytest.fixture()
    def title(self):
        return 'Cool Project'

    @pytest.fixture()
    def title_new(self):
        return 'Super Cool Project'

    @pytest.fixture()
    def collection_one(self, title, user_one):
        return CollectionFactory(title=title, creator=user_one)

    @pytest.fixture()
    def collection_two(self, title, user_one):
        return CollectionFactory(title=title, creator=user_one)

    @pytest.fixture()
    def payload_collection(self, collection_one, title_new, collection_two):
        return {
            'data': [
                {
                    'id': collection_one._id,
                    'type': 'collections',
                    'attributes': {
                        'title': title_new,
                    }
                },
                {
                    'id': collection_two._id,
                    'type': 'collections',
                    'attributes': {
                        'title': title_new,
                    }
                }
            ]
        }

    @pytest.fixture()
    def empty_payload_collection(self, collection_one, collection_two):
        return {
            'data': [
                {'id': collection_one._id, 'type': 'collections', 'attributes': {'title': '', }},
                {'id': collection_two._id, 'type': 'collections', 'attributes': {'title': '', }}
            ]
        }

    @pytest.fixture()
    def url_collections(self):
        return '/{}collections/'.format(API_BASE)

    @pytest.fixture()
    def base_url_collections(self):
        return '/{}collections/{}/'

    def test_non_mutational_collection_bulk_update_tests(
            self, app, payload_collection, url_collections,
            base_url_collections, user_one, title,
            title_new, collection_one, collection_two,
            empty_payload_collection
    ):

        # test_bulk_update_nodes_blank_request
        res = app.put_json_api(
            url_collections, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400

        # test_bulk_update_blank_but_not_empty_title
        payload = {
            'data': [
                {
                    'id': collection_one._id,
                    'type': 'collections',
                    'attributes': {
                        'title': 'This shouldn\'t update.'
                    }
                },
                {
                    'id': collection_two._id,
                    'type': 'collections',
                    'attributes': {
                        'title': ' '
                    }
                }
            ]
        }
        url = base_url_collections.format(API_BASE, collection_one._id)
        res = app.put_json_api(
            url, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_collections_one_not_found
        empty_payload = {'data': [
            {
                'id': '12345',
                'type': 'collections',
                'attributes': {
                    'title': title_new
                }
            }, payload_collection['data'][0]
        ]}

        res = app.put_json_api(
            url_collections, empty_payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to update.'

        url = base_url_collections.format(API_BASE, collection_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_collections_logged_out
        res = app.put_json_api(
            url_collections, payload_collection,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

        url = base_url_collections.format(API_BASE, collection_one._id)
        url_two = base_url_collections.format(API_BASE, collection_two._id)

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        res = app.get(url_two, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_collections_send_dictionary_not_list
        res = app.put_json_api(
            url_collections, {
                'data': {
                    'id': collection_one._id,
                    'type': 'nodes',
                    'attributes': {'title': title_new}
                }},
            auth=user_one.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

        # test_bulk_update_error_formatting
        res = app.put_json_api(
            url_collections, empty_payload_collection,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']], [
                           {'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.'] * 2)

        # test_bulk_update_id_not_supplied
        res = app.put_json_api(
            url_collections, {
                'data': [
                    payload_collection['data'][1],
                    {'type': 'collections',
                     'attributes': {'title': title_new}}
                ]},
            auth=user_one.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/id'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        url = base_url_collections.format(API_BASE, collection_two._id)

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_type_not_supplied
        res = app.put_json_api(
            url_collections, {
                'data': [
                    payload_collection['data'][1],
                    {'id': collection_one._id,
                     'attributes': {'title': title_new}}
                ]},
            auth=user_one.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/type'
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

        url = base_url_collections.format(API_BASE, collection_two._id)

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_incorrect_type
        res = app.put_json_api(
            url_collections, {
                'data': [
                    payload_collection['data'][1],
                    {'id': collection_one._id,
                     'type': 'Incorrect',
                     'attributes': {'title': title_new}}
                ]},
            auth=user_one.auth, expect_errors=True, bulk=True)
        assert res.status_code == 409

        url = base_url_collections.format(API_BASE, collection_two._id)

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

        # test_bulk_update_limits
        node_update_list = {'data': [payload_collection['data'][0]] * 101}
        res = app.put_json_api(
            url_collections, node_update_list,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        # test_bulk_update_no_title
        new_payload = {
            'id': collection_one._id,
            'type': 'collections',
            'attributes': {}}
        res = app.put_json_api(
            url_collections,
            {'data': [payload_collection['data'][1], new_payload]},
            auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        url = base_url_collections.format(API_BASE, collection_two._id)

        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['title'] == title

    def test_bulk_update_collections_logged_in(
            self, app, url_collections, user_one,
            title_new, payload_collection,
            collection_one, collection_two
    ):

        res = app.put_json_api(
            url_collections, payload_collection,
            auth=user_one.auth, bulk=True
        )
        assert res.status_code == 200
        assert ({collection_one._id, collection_two._id} ==
                {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert res.json['data'][0]['attributes']['title'] == title_new
        assert res.json['data'][1]['attributes']['title'] == title_new


@pytest.mark.django_db
class TestNodeBulkDelete:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection_one(self, user_one):
        return CollectionFactory(title='Collection One', creator=user_one)

    @pytest.fixture()
    def collection_two(self, user_one):
        return CollectionFactory(title='Collection Two', creator=user_one)

    @pytest.fixture()
    def collection_three(self, user_one):
        return CollectionFactory(title='Collection Three', creator=user_one)

    @pytest.fixture()
    def collection_user_two(self, user_two):
        return CollectionFactory(title='Collection User Two', creator=user_two)

    @pytest.fixture()
    def url_collections(self):
        return '/{}collections/'.format(API_BASE)

    @pytest.fixture()
    def url_project_one(self, collection_one):
        return '/{}collections/{}/'.format(API_BASE, collection_one._id)

    @pytest.fixture()
    def url_project_two(self, collection_two):
        return '/{}collections/{}/'.format(API_BASE, collection_two._id)

    @pytest.fixture()
    def url_project_private(self, collection_three):
        return '/{}collections/{}/'.format(API_BASE, collection_three._id)

    @pytest.fixture()
    def payload_one(self, collection_one, collection_two):
        return {'data': [{'id': collection_one._id, 'type': 'collections'},
                         {'id': collection_two._id, 'type': 'collections'}]}

    @pytest.fixture()
    def payload_two(self, collection_three):
        return {'data': [{'id': collection_three._id, 'type': 'collections'}]}

    def test_bulk_delete_collections_logged_in(
            self, app, url_collections, payload_one, user_one, url_project_one,
            collection_one, collection_two):

        res = app.delete_json_api(
            url_collections, payload_one,
            auth=user_one.auth, bulk=True
        )
        assert res.status_code == 204

        res = app.get(url_project_one, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 410
        collection_one.reload()
        collection_two.reload()

    def test_bulk_delete_collections_logged_out(
            self, app, url_collections, payload_one,
            user_one, url_project_one, url_project_two
    ):
        res = app.delete_json_api(
            url_collections, payload_one,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

        res = app.get(url_project_one, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200

        res = app.get(url_project_two, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200

    def test_bulk_delete_collections_logged_in_non_contributor(
            self, app, url_collections, payload_two, user_two, user_one,
            url_project_private):

        res = app.delete_json_api(
            url_collections, payload_two,
            auth=user_two.auth, expect_errors=True,
            bulk=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.get(url_project_private, auth=user_one.auth)
        assert res.status_code == 200

    def test_bulk_delete_all_or_nothing(
            self, app, collection_user_two,
            collection_three, url_collections,
            user_one, user_two, url_project_private
    ):
        new_payload = {
            'data': [
                {'id': collection_three._id, 'type': 'collections'},
                {'id': collection_user_two._id, 'type': 'collections'}]}
        res = app.delete_json_api(
            url_collections, new_payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.get(url_project_private, auth=user_one.auth)
        assert res.status_code == 200

        url = '/{}collections/{}/'.format(API_BASE, collection_user_two._id)
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

    def test_non_mutational_node_bulk_delete_tests(
            self, app, url_collections, user_one,
            collection_one, collection_two,
            collection_three, url_project_one,
            payload_one
    ):

        # test_bulk_delete_nodes_blank_request
        res = app.delete_json_api(
            url_collections, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400

        # test_bulk_delete_no_type
        payload = {'data': [
            {'id': collection_one._id},
            {'id': collection_two._id}
        ]}
        res = app.delete_json_api(
            url_collections, payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

        # test_bulk_delete_no_id
        payload = {'data': [
            {'type': 'collections'}
        ]}
        res = app.delete_json_api(
            url_collections, payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/id.'

        # test_bulk_delete_dict_inside_data
        res = app.delete_json_api(
            url_collections,
            {'data': {
                'id': collection_one._id,
                'type': 'collections'}},
            auth=user_one.auth, expect_errors=True,
            bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

        # test_bulk_delete_invalid_type
        res = app.delete_json_api(
            url_collections,
            {'data': [{
                'type': 'Wrong type',
                'id': collection_one._id}
            ]},
            auth=user_one.auth, expect_errors=True,
            bulk=True
        )
        assert res.status_code == 409

        # test_bulk_delete_limits
        new_payload = {
            'data': [{'id': collection_three._id, 'type': 'nodes'}] * 101}
        res = app.delete_json_api(
            url_collections, new_payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        # test_bulk_delete_invalid_payload_one_not_found
        new_payload = {
            'data': [
                payload_one['data'][0], {
                    'id': '12345', 'type': 'collections'}]}
        res = app.delete_json_api(
            url_collections, new_payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Could not find all objects to delete.'

        res = app.get(url_project_one, auth=user_one.auth)
        assert res.status_code == 200

        # test_bulk_delete_no_payload
        res = app.delete_json_api(
            url_collections, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400


@pytest.mark.django_db
class TestCollectionLinksBulkCreate:

    # User_one
    @pytest.fixture()
    def collection_one(self, user_one):
        return CollectionFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def project_one_pointer_private(self, user_one):
        return ProjectFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def project_two_pointer_private(self, user_one):
        return ProjectFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def reg_one_pointer_private(self, user_one):
        return RegistrationFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def reg_two_pointer_private(self, user_one):
        return RegistrationFactory(is_public=False, creator=user_one)

    @pytest.fixture()
    def url_collection_one(self, collection_one):
        return '/{}collections/{}/node_links/'.format(
            API_BASE, collection_one._id)

    @pytest.fixture()
    def payload_collection_one(
            self, project_one_pointer_private, project_two_pointer_private,
            reg_one_pointer_private, reg_two_pointer_private):
        return {
            'data': [{
                'type': 'node_links',
                'relationships': {
                    'target_node': {
                        'data': {
                            'id': project_one_pointer_private._id,
                            'type': 'nodes'
                        }
                    }
                }
            },
                {
                'type': 'node_links',
                'relationships': {
                    'target_node': {
                        'data': {
                            'id': project_two_pointer_private._id,
                            'type': 'nodes'
                        }
                    }
                }
            },
                {
                'type': 'node_links',
                'relationships': {
                    'target_node': {
                        'data': {
                            'id': reg_one_pointer_private._id,
                            'type': 'nodes'
                        }
                    }
                }
            },
                {
                'type': 'node_links',
                'relationships': {
                    'target_node': {
                        'data': {
                            'id': reg_two_pointer_private._id,
                            'type': 'nodes'
                        }
                    }
                }
            }]
        }

    @pytest.fixture()
    def project_one_pointer_public(self, user_one):
        return ProjectFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def project_two_pointer_public(self, user_one):
        return ProjectFactory(is_public=True, creator=user_one)

    # User_two

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection_user_two(self, user_two):
        return CollectionFactory(creator=user_two)

    @pytest.fixture()
    def project_user_two(self, user_two):
        return ProjectFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def registration_user_two(self, user_two):
        return RegistrationFactory(is_public=True, creator=user_two)

    @pytest.fixture()
    def url_user_two(self, collection_user_two):
        return '/{}collections/{}/node_links/'.format(
            API_BASE, collection_user_two._id)

    @pytest.fixture()
    def payload_user_two(self, project_user_two, registration_user_two):
        return {'data':
                [{
                    'type': 'node_links',
                    'relationships': {
                            'nodes': {
                                'data': {
                                    'id': project_user_two._id,
                                    'type': 'nodes'
                                }
                            }
                    }
                },
                    {'type': 'node_links',
                        'relationships': {
                            'nodes': {
                                'data': {
                                    'id': registration_user_two._id,
                                    'type': 'nodes'
                                }
                            }
                        }
                     }]
                }

    def test_bulk_creates_collection_node_pointer_logged_in_contrib(
            self, app, url_collection_one, payload_collection_one, user_one,
            project_one_pointer_private, project_two_pointer_private):

        res = app.post_json_api(
            url_collection_one, payload_collection_one,
            auth=user_one.auth, bulk=True
        )
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == project_one_pointer_private._id

        embedded = res_json[1]['embeds']['target_node']['data']['id']
        assert embedded == project_two_pointer_private._id

        # linked_node endpoint can create linked_registrations,
        # but will not return a valid embed
        embedded = res_json[2]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

        embedded = res_json[3]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

    def test_bulk_creates_node_pointers_collection_to_non_contributing_node(
            self, app, project_user_two, url_collection_one, payload_user_two, user_one):

        res = app.post_json_api(
            url_collection_one, payload_user_two,
            auth=user_one.auth, bulk=True
        )
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == project_user_two._id
        embedded = res_json[1]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

        res = app.get(url_collection_one, auth=user_one.auth)
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == project_user_two._id
        embedded = res_json[1]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

    def test_bulk_creates_node_pointer_already_connected(
            self, app, url_collection_one, payload_collection_one, user_one,
            collection_one, project_one_pointer_private, project_two_pointer_private):

        res = app.post_json_api(
            url_collection_one, payload_collection_one,
            auth=user_one.auth, bulk=True
        )
        assert res.status_code == 201
        assert res.content_type == 'application/vnd.api+json'
        res_json = res.json['data']
        embedded = res_json[0]['embeds']['target_node']['data']['id']
        assert embedded == project_one_pointer_private._id

        embedded_two = res_json[1]['embeds']['target_node']['data']['id']
        assert embedded_two == project_two_pointer_private._id

        # linked_node endpoint can create linked_registrations,
        # but will not return a valid embed
        embedded = res_json[2]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

        embedded = res_json[3]['embeds']['target_node']['errors'][0]['detail']
        assert embedded == 'Not found.'

        res = app.post_json_api(
            url_collection_one, payload_collection_one,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert 'Target Node \'{}\' already pointed to by \'{}\'.'.format(
            project_one_pointer_private._id,
            collection_one._id) in res.json['errors'][0]['detail']

    def test_bulk_create_node_links_blank_request(
            self, app, url_collection_one, user_one):
        res = app.post_json_api(
            url_collection_one, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400

    def test_non_mutational_collection_links_bulk_create_tests(
            self, app, payload_collection_one, url_collection_one, user_one,
            project_one_pointer_private, user_two, collection_user_two):

        # test_bulk_creates_pointers_limits
        payload = {'data': [payload_collection_one['data'][0]] * 101}
        res = app.post_json_api(
            url_collection_one, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        res = app.get(url_collection_one, auth=user_one.auth)
        assert res.json['data'] == []

        # test_bulk_creates_project_target_not_nested
        payload = {
            'data': [{
                'type': 'node_links',
                'target_node_id': project_one_pointer_private._id
            }]
        }
        res = app.post_json_api(
            url_collection_one, payload, auth=user_two.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'

        # test_bulk_creates_collection_node_pointers_logged_out
        res = app.post_json_api(
            url_collection_one, payload_collection_one,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        res = app.get(url_collection_one, auth=user_one.auth)
        assert res.json['data'] == []

        # test_bulk_creates_collection_node_pointer_logged_in_non_contrib
        res = app.post_json_api(
            url_collection_one, payload_collection_one,
            auth=user_two.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 403

        # test_bulk_creates_pointers_non_contributing_node_to_fake_node
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {
            'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = app.post_json_api(
            url_collection_one, fake_payload,
            auth=user_two.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

        # test_bulk_creates_pointers_contributing_node_to_fake_node
        fake_payload = {'data': [{'type': 'node_links', 'relationships': {
            'nodes': {'data': {'id': 'fdxlq', 'type': 'nodes'}}}}]}

        res = app.post_json_api(
            url_collection_one, fake_payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert 'detail' in res.json['errors'][0]

        # test_bulk_creates_fake_nodes_pointing_to_contributing_node
        fake_url = '/{}collections/{}/node_links/'.format(API_BASE, 'fdxlq')

        res = app.post_json_api(
            fake_url, payload_collection_one,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        res = app.post_json_api(
            fake_url, payload_collection_one,
            auth=user_two.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

        # test_bulk_creates_node_pointer_no_type
        payload = {
            'data': [{
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': collection_user_two._id
                        }
                    }
                }
            }]
        }
        res = app.post_json_api(
            url_collection_one, payload,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/0/type'

        # test_bulk_creates_node_pointer_incorrect_type
        payload = {
            'data': [{
                'type': 'Wrong type.',
                'relationships': {
                    'nodes': {
                        'data': {
                            'type': 'nodes',
                            'id': collection_user_two._id
                        }
                    }
                }
            }]
        }
        res = app.post_json_api(
            url_collection_one, payload, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "node_links", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'


@pytest.mark.django_db
class TestBulkDeleteCollectionNodeLinks:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def collection_one(self, user_one):
        return CollectionFactory(creator=user_one)

    @pytest.fixture()
    def project_one_pointer_one(self, user_one):
        return ProjectFactory(creator=user_one, is_public=True)

    @pytest.fixture()
    def project_one_pointer_two(self, user_one):
        return ProjectFactory(creator=user_one, is_public=True)

    @pytest.fixture()
    def collection_one_pointer_one(
            self, collection_one, project_pointer_one,
            user_one
    ):
        return collection_one.collect_object(
            project_pointer_one, user_one)

    @pytest.fixture()
    def collection_one_pointer_two(
            self, collection_one, project_pointer_two,
            user_one
    ):
        return collection_one.collect_object(
            project_pointer_two, user_one)

    @pytest.fixture()
    def payload_collection_one(
            self, collection_one_pointer_one,
            collection_one_pointer_two
    ):
        return {
            'data': [
                {'type': 'node_links', 'id': collection_one_pointer_one._id},
                {'type': 'node_links', 'id': collection_one_pointer_two._id}
            ]
        }

    @pytest.fixture()
    def url_collection_one(self, collection_one):
        return '/{}collections/{}/node_links/'.format(
            API_BASE, collection_one._id)

    @pytest.fixture()
    def collection_two(self, user_one):
        return CollectionFactory(creator=user_one)

    @pytest.fixture()
    def project_two_pointer_one(self, user_one):
        return ProjectFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def project_two_pointer_two(self, user_one):
        return ProjectFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def collection_two_pointer_one(
            self, collection_two, project_two_pointer_one,
            user_one
    ):
        return collection_two.collect_object(
            project_two_pointer_one,
            user_one
        ).guid.referent

    @pytest.fixture()
    def collection_two_pointer_two(
            self, project_two_pointer_two,
            user_one, collection_two
    ):
        return collection_two.collect_object(
            project_two_pointer_two,
            user_one
        ).guid.referent

    @pytest.fixture()
    def payload_collection_two(
            self, collection_two_pointer_one,
            collection_two_pointer_two
    ):
        return {
            'data': [
                {'type': 'node_links', 'id': collection_two_pointer_one._id},
                {'type': 'node_links', 'id': collection_two_pointer_two._id}
            ]
        }

    @pytest.fixture()
    def url_collection_two(self, collection_two):
        return '/{}collections/{}/node_links/'.format(
            API_BASE, collection_two._id)

    def test_bulk_deletes_collection_node_pointers_succeeds_as_owner(
            self, app, collection_two, url_collection_two, payload_collection_two, user_one):

        node_count_before = collection_two.guid_links.count()
        res = app.delete_json_api(
            url_collection_two,
            payload_collection_two,
            auth=user_one.auth, bulk=True
        )
        collection_two.reload()
        assert res.status_code == 204
        assert node_count_before - 2 == collection_two.guid_links.count()
        collection_two.reload()

    def test_return_bulk_deleted_collection_node_pointer(
            self, app, url_collection_two, collection_two,
            payload_collection_two, user_one,
            collection_two_pointer_one
    ):

        res = app.delete_json_api(
            url_collection_two, payload_collection_two,
            auth=user_one.auth, bulk=True
        )
        collection_two.reload()  # Update the model to reflect changes made by post request
        assert res.status_code == 204

        pointer_url = '/{}collections/{}/node_links/{}/'.format(
            API_BASE, collection_two._id, collection_two_pointer_one._id)

        # check that deleted pointer can not be returned
        res = app.get(pointer_url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    def test_non_mutational_bulk_delete_collection_nodelinks_tests(
            self, app, url_collection_two, user_one,
            user_two, payload_collection_two,
            collection_two, url_collection_one,
            collection_two_pointer_one, collection_two_pointer_two
    ):

        # test_bulk_delete_node_links_blank_request
        res = app.delete_json_api(
            url_collection_two, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400

        # test_bulk_delete_pointer_limits
        res = app.delete_json_api(
            url_collection_two,
            {'data': [payload_collection_two['data'][0]] * 101},
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        # test_bulk_delete_dict_inside_data
        res = app.delete_json_api(
            url_collection_two,
            {'data': {
                'id': collection_two._id,
                'type': 'node_links'
            }},
            auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

        # test_bulk_delete_pointers_no_type
        payload = {'data': [
            {'id': collection_two_pointer_one._id},
            {'id': collection_two_pointer_two._id}
        ]}
        res = app.delete_json_api(
            url_collection_two, payload,
            auth=user_one.auth, expect_errors=True,
            bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # test_bulk_delete_pointers_incorrect_type
        payload = {'data': [
            {'id': collection_two_pointer_one._id, 'type': 'Incorrect type.'},
            {'id': collection_two_pointer_two._id, 'type': 'Incorrect type.'}
        ]}
        res = app.delete_json_api(
            url_collection_two, payload,
            auth=user_one.auth, expect_errors=True,
            bulk=True)
        assert res.status_code == 409

        # test_bulk_delete_pointers_no_id
        payload = {'data': [
            {'type': 'node_links'},
            {'type': 'node_links'}
        ]}
        res = app.delete_json_api(
            url_collection_two, payload,
            auth=user_one.auth, expect_errors=True,
            bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

        # test_bulk_delete_pointers_no_data
        res = app.delete_json_api(
            url_collection_two, auth=user_one.auth,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must contain array of resource identifier objects.'

        # test_bulk_delete_pointers_payload_is_empty_dict
        res = app.delete_json_api(
            url_collection_two, {},
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'

        # test_bulk_deletes_collection_node_pointers_logged_out
        res = app.delete_json_api(
            url_collection_two, payload_collection_two,
            expect_errors=True, bulk=True
        )
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        # test_bulk_deletes_collection_node_pointers_fails_if_bad_auth
        node_count_before = collection_two.guid_links.count()
        res = app.delete_json_api(
            url_collection_two, payload_collection_two,
            auth=user_two.auth, expect_errors=True, bulk=True
        )
        # This is could arguably be a 405, but we don't need to go crazy with
        # status codes
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]
        collection_two.reload()
        assert node_count_before == collection_two.guid_links.count()

        # Regression test for https://openscience.atlassian.net/browse/OSF-4322
        # test_bulk_delete_link_that_is_not_linked_to_correct_node
        ProjectFactory(creator=user_one)
        # The node link belongs to a different project
        res = app.delete_json_api(
            url_collection_one, payload_collection_two,
            auth=user_one.auth, expect_errors=True, bulk=True
        )
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Node link does not belong to the requested node.'


@pytest.mark.django_db
class TestCollectionRelationshipNodeLinks:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def auth_user_one(self, user_one):
        return Auth(user_one)

    @pytest.fixture()
    def node_admin(self, user_one):
        return NodeFactory(creator=user_one)

    @pytest.fixture()
    def node_contributor(self, user_one, user_two):
        node_contributor = NodeFactory(creator=user_two)
        node_contributor.add_contributor(user_one, auth=Auth(user_two))
        node_contributor.save()
        return node_contributor

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def node_private(self, user_one):
        return NodeFactory(creator=user_one)

    @pytest.fixture()
    def registration_private(self, user_one):
        return RegistrationFactory(creator=user_one)

    @pytest.fixture()
    def node_public(self):
        return NodeFactory(is_public=True)

    @pytest.fixture()
    def registration_public(self):
        return RegistrationFactory(is_public=True)

    @pytest.fixture()
    def collection_private(
            self, user_one, node_private,
            registration_private, auth_user_one
    ):
        collection_private = CollectionFactory(creator=user_one)
        collection_private.collect_object(node_private, user_one)
        collection_private.collect_object(
            registration_private, user_one
        )
        return collection_private

    @pytest.fixture()
    def collection_public(
            self, node_private, registration_private,
            user_two, node_public, registration_public):

        collection_public = CollectionFactory(is_public=True, creator=user_two)
        collection_public.collect_object(node_private, user_two)
        collection_public.collect_object(
            registration_private, user_two)
        collection_public.collect_object(node_public, user_two)
        collection_public.collect_object(registration_public, user_two)
        return collection_public

    @pytest.fixture()
    def url_private_linked_nodes(self, collection_private):
        return '/{}collections/{}/relationships/linked_nodes/'.format(
            API_BASE, collection_private._id)

    @pytest.fixture()
    def url_private_linked_regs(self, collection_private):
        return '/{}collections/{}/relationships/linked_registrations/'.format(
            API_BASE, collection_private._id)

    @pytest.fixture()
    def url_public_linked_nodes(self, collection_public):
        return '/{}collections/{}/relationships/linked_nodes/'.format(
            API_BASE, collection_public._id)

    @pytest.fixture()
    def url_public_linked_regs(self, collection_public):
        return '/{}collections/{}/relationships/linked_registrations/'.format(
            API_BASE, collection_public._id)

    @pytest.fixture()
    def make_payload(self, node_admin):
        def payload(node_ids=None):
            node_ids = node_ids or [node_admin._id]
            env_linked_nodes = [{'type': 'linked_nodes',
                                 'id': node_id} for node_id in node_ids]
            return {'data': env_linked_nodes}
        return payload

    def test_get_relationship_linked_nodes(
            self, app, url_private_linked_nodes,
            user_one, collection_private, node_private
    ):
        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        assert res.status_code == 200
        assert collection_private.linked_nodes_self_url in res.json['links']['self']
        assert collection_private.linked_nodes_related_url in res.json['links']['html']
        assert res.json['data'][0]['id'] == node_private._id

    def test_get_relationship_linked_registrations(
            self, app, registration_private,
            url_private_linked_regs, user_one,
            collection_private
    ):
        res = app.get(url_private_linked_regs, auth=user_one.auth)
        assert res.status_code == 200
        assert collection_private.linked_registrations_self_url in res.json['links']['self']
        assert collection_private.linked_registrations_related_url in res.json['links']['html']
        assert res.json['data'][0]['id'] == registration_private._id

    def test_get_public_relationship_linked_nodes_logged_out(
            self, app, url_public_linked_nodes, node_public):
        res = app.get(url_public_linked_nodes)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == node_public._id

    def test_get_public_relationship_linked_registrations_logged_out(
            self, app, url_public_linked_regs, registration_public):
        res = app.get(url_public_linked_regs)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == registration_public._id

    def test_get_public_relationship_linked_nodes_logged_in(
            self, app, url_public_linked_nodes, user_one):
        res = app.get(url_public_linked_nodes, auth=user_one.auth)

        assert res.status_code == 200
        assert len(res.json['data']) == 2

    def test_get_public_relationship_linked_registrations_logged_in(
            self, app, url_public_linked_regs, user_one):
        res = app.get(url_public_linked_regs, auth=user_one.auth)

        assert res.status_code == 200
        assert len(res.json['data']) == 2

    def test_post_contributing_node(
            self, app, url_private_linked_nodes,
            make_payload, user_one, node_contributor,
            node_private
    ):
        res = app.post_json_api(
            url_private_linked_nodes, make_payload([node_contributor._id]),
            auth=user_one.auth
        )

        assert res.status_code == 201

        ids = [data['id'] for data in res.json['data']]
        assert node_contributor._id in ids
        assert node_private._id in ids

    def test_post_public_node(
            self, app, url_private_linked_nodes,
            node_public, make_payload, node_private,
            user_one
    ):
        res = app.post_json_api(
            url_private_linked_nodes, make_payload([node_public._id]),
            auth=user_one.auth
        )

        assert res.status_code == 201

        ids = [data['id'] for data in res.json['data']]
        assert node_public._id in ids
        assert node_private._id in ids

    def test_post_node_already_linked(
            self, app, user_one,
            url_private_linked_nodes,
            make_payload, node_private
    ):
        res = app.post_json_api(
            url_private_linked_nodes, make_payload([node_private._id]),
            auth=user_one.auth
        )

        assert res.status_code == 204

    def test_put_contributing_node(
            self, app, url_private_linked_nodes,
            make_payload, node_contributor,
            user_one, node_private
    ):
        res = app.put_json_api(
            url_private_linked_nodes, make_payload([node_contributor._id]),
            auth=user_one.auth
        )

        assert res.status_code == 200

        ids = [data['id'] for data in res.json['data']]
        assert node_contributor._id in ids
        assert node_private._id not in ids

    def test_delete_with_put_empty_array(
            self, app, user_one, url_private_linked_nodes, make_payload,
            collection_private, node_admin, auth_user_one):

        collection_private.collect_object(node_admin, user_one)
        payload = make_payload()
        payload['data'].pop()
        res = app.put_json_api(
            url_private_linked_nodes, payload,
            auth=user_one.auth
        )
        assert res.status_code == 200
        assert res.json['data'] == payload['data']

    def test_delete_one(
            self, app, make_payload, url_private_linked_nodes, node_admin,
            node_private, user_one, auth_user_one, collection_private):

        collection_private.collect_object(node_admin, user_one)
        res = app.delete_json_api(
            url_private_linked_nodes, make_payload([node_private._id]),
            auth=user_one.auth,
        )
        assert res.status_code == 204

        res = app.get(url_private_linked_nodes, auth=user_one.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_admin._id in ids
        assert node_private._id not in ids

    def test_delete_multiple(
            self, app, url_private_linked_nodes, user_one, collection_private,
            node_private, make_payload, node_admin, auth_user_one):

        collection_private.collect_object(node_admin, user_one)
        res = app.delete_json_api(url_private_linked_nodes, make_payload(
            [node_private._id, node_admin._id]), auth=user_one.auth, )
        assert res.status_code == 204

        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        assert res.json['data'] == []

    def test_delete_not_present(
            self, app, make_payload,
            url_private_linked_nodes,
            url_private_linked_regs,
            collection_private, node, user_one
    ):

        number_of_links = collection_private.guid_links.count()
        res = app.delete_json_api(
            url_private_linked_nodes, make_payload([node._id]), auth=user_one.auth)
        assert res.status_code == 204

        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        reg_res = app.get(url_private_linked_regs, auth=user_one.auth)
        assert len(res.json['data']) + \
            len(reg_res.json['data']) == number_of_links

    def test_node_links_and_relationship_represent_same_nodes(
            self, app, user_one, url_private_linked_nodes, auth_user_one,
            node_admin, node_contributor, collection_private):

        collection_private.collect_object(node_admin, user_one)
        collection_private.collect_object(node_contributor, user_one)
        res_relationship = app.get(
            url_private_linked_nodes,
            auth=user_one.auth)
        res_node_links = app.get(
            '/{}collections/{}/node_links/'.format(
                API_BASE,
                collection_private._id),
            auth=user_one.auth)
        node_links_id = []
        for data in res_node_links.json['data']:
            try:
                node_links_id.append(
                    data['embeds']['target_node']['data']['id'])
            # node_links does not handle registrations correctly, skip them
            except KeyError:
                continue
        relationship_id = [data['id']
                           for data in res_relationship.json['data']]

        assert set(node_links_id) == set(relationship_id)

    def test_non_mutational_collection_relationship_nodeLinks_tests(
            self, app, user_one, user_two,
            url_private_linked_nodes, node,
            node_private, make_payload,
            url_private_linked_regs,
            node_contributor,
            url_public_linked_nodes,
            node_public
    ):

        # test_get_private_relationship_linked_nodes_logged_out
        res = app.get(url_private_linked_nodes, expect_errors=True)

        assert res.status_code == 401

        # test_get_private_relationship_linked_registrations_logged_out
        res = app.get(url_private_linked_regs, expect_errors=True)

        assert res.status_code == 401

        # test_post_private_node
        res = app.post_json_api(
            url_private_linked_nodes, make_payload([node._id]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 403

        res = app.get(url_private_linked_nodes, auth=user_one.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node._id not in ids
        assert node_private._id in ids

        # test_post_mixed_nodes
        res = app.post_json_api(
            url_private_linked_nodes, make_payload([node._id, node_contributor._id]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 403

        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        ids = [data['id'] for data in res.json['data']]
        assert node._id not in ids
        assert node_contributor._id not in ids
        assert node_private._id in ids

        # test_put_private_node
        res = app.put_json_api(
            url_private_linked_nodes, make_payload([node._id]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 403

        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        ids = [data['id'] for data in res.json['data']]
        assert node._id not in ids
        assert node_private._id in ids

        # test_put_mixed_nodes
        res = app.put_json_api(
            url_private_linked_nodes, make_payload([node._id, node_contributor._id]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 403

        res = app.get(url_private_linked_nodes, auth=user_one.auth)
        ids = [data['id'] for data in res.json['data']]
        assert node._id not in ids
        assert node_contributor._id not in ids
        assert node_private._id in ids

        # test_access_other_collection
        collection = CollectionFactory(creator=user_two)
        url = '/{}collections/{}/relationships/linked_nodes/'.format(
            API_BASE, collection._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 403

        # test_node_doesnt_exist
        res = app.post_json_api(
            url_private_linked_nodes, make_payload(['aquarela']),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 404

        # test_type_mistyped
        res = app.post_json_api(
            url_private_linked_nodes,
            {'data': [{
                'type': 'not_linked_nodes',
                'id': node_contributor._id}
            ]},
            auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

        # test_creates_public_linked_node_relationship_logged_out
        res = app.post_json_api(url_public_linked_nodes, make_payload(
            [node_public._id]), expect_errors=True)
        assert res.status_code == 401

        # test_creates_public_linked_node_relationship_logged_in
        res = app.post_json_api(
            url_public_linked_nodes,
            make_payload([node_public._id]),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_creates_private_linked_node_relationship_logged_out
        res = app.post_json_api(
            url_private_linked_nodes,
            make_payload([node._id]),
            expect_errors=True
        )
        assert res.status_code == 401

        # test_put_public_nodes_relationships_logged_out
        res = app.put_json_api(
            url_public_linked_nodes,
            make_payload([node_public._id]),
            expect_errors=True
        )
        assert res.status_code == 401

        # test_put_public_nodes_relationships_logged_in
        res = app.put_json_api(
            url_public_linked_nodes,
            make_payload([node_private._id]),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_delete_public_nodes_relationships_logged_out
        res = app.delete_json_api(
            url_public_linked_nodes,
            make_payload([node_public._id]),
            expect_errors=True
        )
        assert res.status_code == 401

        # test_delete_public_nodes_relationships_logged_in
        res = app.delete_json_api(
            url_public_linked_nodes,
            make_payload([node_private._id]),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_attempt_to_add_collection_to_collection
        collection = CollectionFactory(creator=user_one)
        res = app.post_json_api(
            url_private_linked_nodes,
            make_payload([collection._id]),
            auth=user_one.auth, expect_errors=True
        )
        assert res.status_code == 404


@pytest.mark.django_db
class TestCollectionLinkedNodes:

    @pytest.fixture()
    def auth_user(self, user_one):
        return Auth(user_one)

    @pytest.fixture()
    def linked_node_one(self, user_one):
        return NodeFactory(creator=user_one)

    @pytest.fixture()
    def linked_node_two(self, user_one):
        return NodeFactory(creator=user_one)

    @pytest.fixture()
    def linked_registration_one(self, user_one):
        return RegistrationFactory(creator=user_one)

    @pytest.fixture()
    def linked_registration_two(self, user_one):
        return RegistrationFactory(creator=user_one)

    @pytest.fixture()
    def node_public(self, user_one):
        return NodeFactory(creator=user_one, is_public=True)

    @pytest.fixture()
    def registration_public(self, user_one):
        return RegistrationFactory(is_public=True, creator=user_one)

    @pytest.fixture()
    def collection(
            self, user_one, linked_node_one,
            linked_registration_one,
            linked_registration_two,
            linked_node_two, node_public,
            registration_public, auth_user
    ):

        collection = CollectionFactory(creator=user_one)
        collection.collect_object(linked_node_one, user_one)
        collection.collect_object(linked_node_two, user_one)
        collection.collect_object(linked_registration_one, user_one)
        collection.collect_object(linked_registration_two, user_one)
        collection.collect_object(node_public, user_one)
        collection.collect_object(registration_public, user_one)
        collection.save()
        return collection

    @pytest.fixture()
    def url_collection_linked_nodes(self, collection):
        return '/{}collections/{}/linked_nodes/'.format(
            API_BASE, collection._id)

    @pytest.fixture()
    def url_collection_linked_regs(self, collection):
        return '/{}collections/{}/linked_registrations/'.format(
            API_BASE, collection._id)

    @pytest.fixture()
    def id_linked_nodes(self, collection):
        return list(
            collection.guid_links.values_list(
                '_id', flat=True)
        )

    def test_linked_nodes_returns_everything(
            self, app, url_collection_linked_nodes, url_collection_linked_regs,
            user_one, id_linked_nodes):

        res = app.get(url_collection_linked_nodes, auth=user_one.auth)
        reg_res = app.get(url_collection_linked_regs, auth=user_one.auth)

        assert res.status_code == 200
        nodes_returned = [linked_node['id']
                          for linked_node in res.json['data']]
        registrations_returned = [linked_registration['id']
                                  for linked_registration in reg_res.json['data']]
        assert len(nodes_returned) + \
            len(registrations_returned) == len(id_linked_nodes)

        for node_returned in nodes_returned:
            assert node_returned in id_linked_nodes
        for registration_returned in registrations_returned:
            assert registration_returned in id_linked_nodes

    def test_linked_nodes_only_return_viewable_nodes(
            self, app, linked_node_one,
            linked_node_two, linked_registration_one,
            linked_registration_two, node_public,
            registration_public, id_linked_nodes,
            auth_user
    ):

        user = AuthUserFactory()
        collection = CollectionFactory(creator=user)
        linked_node_one.add_contributor(user, auth=auth_user, save=True)
        linked_node_two.add_contributor(user, auth=auth_user, save=True)
        linked_registration_one.add_contributor(
            user, auth=auth_user, save=True)
        linked_registration_two.add_contributor(
            user, auth=auth_user, save=True)
        node_public.add_contributor(user, auth=auth_user, save=True)
        registration_public.add_contributor(user, auth=auth_user, save=True)
        collection.collect_object(linked_node_one, user)
        collection.collect_object(linked_node_two, user)
        collection.collect_object(linked_registration_one, user)
        collection.collect_object(linked_registration_two, user)
        collection.collect_object(node_public, user)
        collection.collect_object(registration_public, user)
        collection.save()

        res = app.get('/{}collections/{}/linked_nodes/'.format(API_BASE,
                                                               collection._id), auth=user.auth)
        reg_res = app.get(
            '/{}collections/{}/linked_registrations/'.format(API_BASE, collection._id), auth=user.auth)

        assert res.status_code == 200
        assert reg_res.status_code == 200
        nodes_returned = [linked_node['id']
                          for linked_node in res.json['data']]
        registrations_returned = [linked_registration['id']
                                  for linked_registration in res.json['data']]
        assert len(nodes_returned) + \
            len(registrations_returned) == len(id_linked_nodes)

        for node_returned in nodes_returned:
            assert node_returned in id_linked_nodes
        for registration_returned in registrations_returned:
            assert registration_returned in id_linked_nodes

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            linked_node_two.remove_contributor(user, auth=auth_user)
            node_public.remove_contributor(user, auth=auth_user)
            linked_registration_two.remove_contributor(user, auth=auth_user)
            registration_public.remove_contributor(user, auth=auth_user)

        res = app.get(
            '/{}collections/{}/linked_nodes/'.format(
                API_BASE, collection._id
            ), auth=user.auth
        )
        reg_res = app.get(
            '/{}collections/{}/linked_registrations/'.format(
                API_BASE, collection._id
            ), auth=user.auth
        )

        nodes_returned = [linked_node['id']
                          for linked_node in res.json['data']]
        registrations_returned = [linked_registration['id']
                                  for linked_registration in reg_res.json['data']]

        assert len(nodes_returned) + \
            len(registrations_returned) == len(id_linked_nodes) - 2
        assert linked_node_one._id in nodes_returned
        assert node_public._id in nodes_returned
        assert linked_registration_one._id in registrations_returned
        assert registration_public._id in registrations_returned
        assert linked_node_two._id not in nodes_returned
        assert linked_registration_two._id not in registrations_returned

    def test_linked_nodes_doesnt_return_deleted_nodes(
            self, app, linked_node_one, linked_node_two,
            node_public, registration_public,
            id_linked_nodes, url_collection_linked_nodes,
            url_collection_linked_regs, user_one,
            linked_registration_one,
            linked_registration_two
    ):

        linked_node_one.is_deleted = True
        linked_node_one.save()
        res = app.get(url_collection_linked_nodes, auth=user_one.auth)

        linked_registration_one.is_deleted = True
        linked_registration_one.save()
        reg_res = app.get(url_collection_linked_regs, auth=user_one.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id'] for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(id_linked_nodes) - 4

        assert reg_res.status_code == 200
        registrations_returned = [
            linked_registration['id'] for linked_registration in reg_res.json['data']
        ]
        assert len(registrations_returned) == len(id_linked_nodes) - 4

        assert linked_node_one._id not in nodes_returned
        assert linked_node_two._id in nodes_returned
        assert node_public._id in nodes_returned

        assert linked_registration_one._id not in registrations_returned
        assert linked_registration_two._id in registrations_returned
        assert registration_public._id in registrations_returned

    def test_attempt_to_return_linked_nodes_logged_out(
            self, app, url_collection_linked_nodes):

        res = app.get(
            url_collection_linked_nodes,
            auth=None, expect_errors=True
        )
        assert res.status_code == 401
