import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory,
)
from osf.utils import permissions


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeSparseFieldsList:

    @pytest.fixture()
    def deleted_project(self):
        return ProjectFactory(is_deleted=True)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def url(self):
        return '/{}nodes/?fields[nodes]='.format(API_BASE)

    def test_node_sparse_fields_list(
            self, app, user, deleted_project,
            private_project, public_project, url):

        #   test_empty_fields_returns_no_attributes
        res = app.get(url)
        node_json = res.json['data'][0]

        assert node_json['attributes'] == {}
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes'])

    #   test_sparse_fields_includes_relationships
        res = app.get(url + 'children')
        node_json = res.json['data'][0]

        assert node_json['attributes'] == {}
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes', 'relationships'])
        assert node_json['relationships']['children']['links']['related']['href'].endswith(
            '/{}nodes/{}/children/'.format(API_BASE, public_project._id))

    #   test_returns_expected_nodes
        res = app.get(url + 'title')
        data = res.json['data']

        ids = [each['id'] for each in data]
        assert public_project._id in ids
        assert deleted_project._id not in ids
        assert private_project._id not in ids

        assert len(data) == 1
        node_json = data[0]
        assert node_json['attributes']['title'] == public_project.title
        assert len(node_json['attributes']) == 1
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes'])

    #   test_filtering_by_id
        url = '/{}nodes/?filter[id]={}&fields[nodes]='.format(
            API_BASE, public_project._id)
        res = app.get(url)
        assert [
            each['id'] for each in res.json['data']] == [
            public_project._id]

        node_json = res.json['data'][0]
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes'])
        assert node_json['attributes'] == {}

    #   test_filtering_by_excluded_field
        url = '/{}nodes/?filter[title]={}&fields[nodes]='.format(
            API_BASE, public_project.title)
        res = app.get(url)
        assert [
            each['id'] for each in res.json['data']] == [
            public_project._id]

        node_json = res.json['data'][0]
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes'])
        assert node_json['attributes'] == {}

    #   test_create_with_sparse_fields
        payload = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': 'New Title',
                        'description': 'What a test',
                        'category': 'project',
                        'public': True,
                    }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert set(res.json['data'].keys()) == set(
            ['links', 'type', 'id', 'attributes'])
        assert res.json['data']['attributes'] == {}


@pytest.mark.django_db
class TestNodeSparseFieldsDetail:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def url(self, node):
        return '/{}nodes/{}/'.format(API_BASE, node._id)

    def test_node_sparse_fields_detail_non_mutating_tests(
            self, app, user, node, url):

        #   test_empty_fields_returns_no_attributes
        res = app.get(url + '?fields[nodes]=')
        node_json = res.json['data']

        assert node_json['attributes'] == {}
        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes'])

    #   test_embed_sparse_same_type
        child = ProjectFactory(parent=node, is_public=True, creator=user)
        res_url = '{}?embed=children&fields[nodes]=title,children'.format(url)
        res = app.get(res_url)
        node_json = res.json['data']

        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes', 'relationships', 'embeds'])
        assert node_json['attributes'].keys() == ['title']
        assert set(node_json['embeds']['children']['data'][0].keys()) == set(
            ['links', 'type', 'id', 'attributes', 'relationships'])
        assert node_json['embeds']['children']['data'][0]['attributes'].keys() == [
            'title']
        assert node_json['embeds']['children']['data'][0]['attributes']['title'] == child.title

    #   test_embed_sparse_different_types
        res_url = '{}?embed=contributors&fields[nodes]=title,contributors'.format(
            url)
        res = app.get(res_url)
        node_json = res.json['data']

        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
        assert node_json['attributes'].keys() == ['title']
        assert len(node_json['embeds']['contributors']['data']) == 1
        assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(
            node._id, user._id)
        assert len(node_json['embeds']['contributors']
                   ['data'][0]['attributes']) > 1

    #   test_sparse_embedded_type
        res_url = '{}?embed=contributors&fields[contributors]='.format(url)
        res = app.get(res_url)
        node_json = res.json['data']

        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
        assert len(node_json['attributes'].keys()) > 1
        assert len(node_json['embeds']['contributors']['data']) == 1
        assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(
            node._id, user._id)
        assert len(node_json['embeds']['contributors']
                   ['data'][0]['attributes']) == 0

    #   test_multiple_sparse_types
        res_url = '{}?fields[nodes]=contributors,title&embed=contributors&fields[contributors]=bibliographic'.format(
            url)
        res = app.get(res_url)
        node_json = res.json['data']

        assert set(node_json.keys()) == set(
            ['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
        assert node_json['attributes'].keys() == ['title']
        assert len(node_json['embeds']['contributors']['data']) == 1
        assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(
            node._id, user._id)
        assert node_json['embeds']['contributors']['data'][0]['attributes'].keys() == [
            'bibliographic']

    def test_update_with_sparse_fields(self, app, user, node, url):
        res_url = '{}?fields[nodes]='.format(url)
        old_title = node.title
        payload = {'data': {
            'id': node._id,
            'type': 'nodes',
            'attributes': {
                'title': 'new title'
            }
        }}
        res = app.patch_json_api(res_url, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes'] == {}
        node.reload()
        assert node.title != old_title
        assert node.title == 'new title'


@pytest.mark.django_db
class TestSparseViewOnlyLinks:

    @pytest.fixture()
    def creation_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def viewing_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contributing_read_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contributing_write_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def private_node_one(
            self, creation_user,
            contributing_read_user,
            contributing_write_user):
        private_node_one = ProjectFactory(
            is_public=False,
            creator=creation_user,
            title='Private One')
        private_node_one.add_contributor(
            contributing_read_user,
            permissions=[permissions.READ], save=True)
        private_node_one.add_contributor(
            contributing_write_user,
            permissions=[permissions.READ, permissions.WRITE],
            save=True)
        return private_node_one

    @pytest.fixture()
    def private_node_one_anonymous_link(self, private_node_one):
        private_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
        private_node_one_anonymous_link.nodes.add(private_node_one)
        private_node_one_anonymous_link.save()
        return private_node_one_anonymous_link

    @pytest.fixture()
    def private_node_one_url(self, private_node_one):
        return '/{}nodes/{}/'.format(API_BASE, private_node_one._id)

    def test_sparse_fields_with_anonymous_link(
            self, app, private_node_one_url, private_node_one_anonymous_link):
        res = app.get(private_node_one_url, {
            'view_only': private_node_one_anonymous_link.key,
            'fields[nodes]': 'title,current_user_can_comment,contributors',
            'fields[contributors]': 'id',
            'embed': 'contributors'
        })  # current_user_can_comment is an anonymized field, should be removed
        assert res.status_code == 200
        assert res.json['data']['attributes'].keys() == ['title']

        for contrib in res.json['data']['embeds']['contributors']['data']:
            assert contrib['id'] == ''
            assert contrib['attributes'] == {}
