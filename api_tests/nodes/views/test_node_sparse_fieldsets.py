import pytest

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)

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

    def test_node_sparse_fields_list(self, app, user, deleted_project, private_project, public_project, url):

    # def test_empty_fields_returns_no_attributes(self):
        res = app.get(url)
        node_json = res.json['data'][0]

        assert node_json['attributes'] == {}
        assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes'])

    # def test_sparse_fields_includes_relationships(self):
        res = app.get(url + 'children')
        node_json = res.json['data'][0]

        assert node_json['attributes'] == {}
        assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes', 'relationships'])
        assert node_json['relationships']['children']['links']['related']['href'].endswith('/{}nodes/{}/children/'.format(API_BASE, public_project._id))

    # def test_returns_expected_nodes(self):
        res = app.get(url + 'title')
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert public_project._id in ids
        assert deleted_project._id not in ids
        assert private_project._id not in ids

        assert len(node_json) == 1
        node_json = node_json[0]
        assert node_json['attributes']['title'] == public_project.title
        assert len(node_json['attributes']) == 1
        assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes'])

    # def test_filtering_by_id(self):
        url = '/{}nodes/?filter[id]={}&fields[nodes]='.format(API_BASE, public_project._id)
        res = app.get(url)
        assert [each['id'] for each in res.json['data']] == [public_project._id]

        node_json = res.json['data'][0]
        assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes'])
        assert node_json['attributes'] == {}

    # def test_filtering_by_excluded_field(self):
        url = '/{}nodes/?filter[title]={}&fields[nodes]='.format(API_BASE, public_project.title)
        res = app.get(url)
        assert [each['id'] for each in res.json['data']] == [public_project._id]

        node_json = res.json['data'][0]
        assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes'])
        assert node_json['attributes'] == {}

    # def test_create_with_sparse_fields(self):
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
        assert set(res.json['data'].keys()) == set(['links', 'type', 'id', 'attributes'])
        assert res.json['data']['attributes'] == {}

# class TestNodeSparseFieldsDetail(ApiTestCase):

#     def setUp(self):
#         super(TestNodeSparseFieldsDetail, self).setUp()
#         self.user = AuthUserFactory()
#         self.node = ProjectFactory(is_public=True, creator=self.user)
#         self.url = '/{}nodes/{}/'.format(API_BASE, self.node._id)

#     def test_empty_fields_returns_no_attributes(self):
#         res = self.app.get(self.url + '?fields[nodes]=')
#         node_json = res.json['data']

#         assert node_json['attributes'] == {}
#         assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes'])

#     def test_embed_sparse_same_type(self):
#         child = ProjectFactory(parent=self.node, is_public=True, creator=self.user)
#         url = '{}?embed=children&fields[nodes]=title,children'.format(self.url)
#         res = self.app.get(url)
#         node_json = res.json['data']

#         assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes', 'relationships', 'embeds'])
#         assert node_json['attributes'].keys() == ['title']
#         assert set(node_json['embeds']['children']['data'][0].keys()) == set(['links', 'type', 'id', 'attributes', 'relationships'])
#         assert node_json['embeds']['children']['data'][0]['attributes'].keys() == ['title']
#         assert node_json['embeds']['children']['data'][0]['attributes']['title'] == child.title

#     def test_embed_sparse_different_types(self):
#         url = '{}?embed=contributors&fields[nodes]=title,contributors'.format(self.url)
#         res = self.app.get(url)
#         node_json = res.json['data']

#         assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
#         assert node_json['attributes'].keys() == ['title']
#         assert len(node_json['embeds']['contributors']['data']) == 1
#         assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(self.node._id, self.user._id)
#         assert len(node_json['embeds']['contributors']['data'][0]['attributes']) > 1

#     def test_sparse_embedded_type(self):
#         url = '{}?embed=contributors&fields[contributors]='.format(self.url)
#         res = self.app.get(url)
#         node_json = res.json['data']

#         assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
#         assert len(node_json['attributes'].keys()) > 1
#         assert len(node_json['embeds']['contributors']['data']) == 1
#         assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(self.node._id, self.user._id)
#         assert len(node_json['embeds']['contributors']['data'][0]['attributes']) == 0

#     def test_multiple_sparse_types(self):
#         url = '{}?fields[nodes]=contributors,title&embed=contributors&fields[contributors]=bibliographic'.format(self.url)
#         res = self.app.get(url)
#         node_json = res.json['data']

#         assert set(node_json.keys()) == set(['links', 'type', 'id', 'attributes', 'embeds', 'relationships'])
#         assert node_json['attributes'].keys() == ['title']
#         assert len(node_json['embeds']['contributors']['data']) == 1
#         assert node_json['embeds']['contributors']['data'][0]['id'] == '{}-{}'.format(self.node._id, self.user._id)
#         assert node_json['embeds']['contributors']['data'][0]['attributes'].keys() == ['bibliographic']

#     def test_update_with_sparse_fields(self):
#         url = '{}?fields[nodes]='.format(self.url)
#         old_title = self.node.title
#         payload = {'data': {
#             'id': self.node._id,
#             'type': 'nodes',
#             'attributes': {
#                 'title': 'new title'
#             }
#         }}
#         res = self.app.patch_json_api(url, payload, auth=self.user.auth)
#         assert res.status_code == 200
#         assert res.json['data']['attributes'] == {}
#         self.node.reload()
#         assert self.node.title != old_title


# class TestSparseViewOnlyLinks(ViewOnlyTestCase):

#     def test_sparse_fields_with_anonymous_link(self):
#         res = self.app.get(self.private_node_one_url, {
#             'view_only': self.private_node_one_anonymous_link.key,
#             'fields[nodes]': 'title,current_user_can_comment,contributors',
#             'fields[contributors]': 'id',
#             'embed': 'contributors'
#         })  # current_user_can_comment is an anonymized field, should be removed
#         assert res.status_code == 200
#         assert res.json['data']['attributes'].keys() == ['title']

#         for contrib in res.json['data']['embeds']['contributors']['data']:
#             assert contrib['id'] == ''
#             assert contrib['attributes'] == {}
