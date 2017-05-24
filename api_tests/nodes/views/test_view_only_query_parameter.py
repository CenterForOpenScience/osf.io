import pytest

from website.util import permissions
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from website.models import Node
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory,
)

class ViewOnlyTestCase(object):

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.creation_user = AuthUserFactory()
        self.viewing_user = AuthUserFactory()
        self.contributing_read_user = AuthUserFactory()
        self.contributing_write_user = AuthUserFactory()
        self.valid_contributors = [
            self.creation_user._id,
            self.contributing_read_user._id,
            self.contributing_write_user._id,
        ]

        self.private_node_one = ProjectFactory(is_public=False, creator=self.creation_user, title="Private One")
        self.private_node_one.add_contributor(self.contributing_read_user, permissions=[permissions.READ], save=True)
        self.private_node_one.add_contributor(self.contributing_write_user, permissions=[permissions.WRITE], save=True)
        self.private_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
        self.private_node_one_anonymous_link.nodes.add(self.private_node_one)
        self.private_node_one_anonymous_link.save()
        self.private_node_one_private_link = PrivateLinkFactory(anonymous=False)
        self.private_node_one_private_link.nodes.add(self.private_node_one)
        self.private_node_one_private_link.save()
        self.private_node_one_url = '/{}nodes/{}/'.format(API_BASE, self.private_node_one._id)

        self.private_node_two = ProjectFactory(is_public=False, creator=self.creation_user, title="Private Two")
        self.private_node_two.add_contributor(self.contributing_read_user, permissions=[permissions.READ], save=True)
        self.private_node_two.add_contributor(self.contributing_write_user, permissions=[permissions.WRITE], save=True)
        self.private_node_two_url = '/{}nodes/{}/'.format(API_BASE, self.private_node_two._id)

        self.public_node_one = ProjectFactory(is_public=True, creator=self.creation_user, title="Public One")
        self.public_node_one.add_contributor(self.contributing_read_user, permissions=[permissions.READ], save=True)
        self.public_node_one.add_contributor(self.contributing_write_user, permissions=[permissions.WRITE], save=True)
        self.public_node_one_anonymous_link = PrivateLinkFactory(anonymous=True)
        self.public_node_one_anonymous_link.nodes.add(self.public_node_one)
        self.public_node_one_anonymous_link.save()
        self.public_node_one_private_link = PrivateLinkFactory(anonymous=False)
        self.public_node_one_private_link.nodes.add(self.public_node_one)
        self.public_node_one_private_link.save()
        self.public_node_one_url = '/{}nodes/{}/'.format(API_BASE, self.public_node_one._id)

        self.public_node_two = ProjectFactory(is_public=True, creator=self.creation_user, title="Public Two")
        self.public_node_two.add_contributor(self.contributing_read_user, permissions=[permissions.READ], save=True)
        self.public_node_two.add_contributor(self.contributing_write_user, permissions=[permissions.WRITE], save=True)
        self.public_node_two_url = '/{}nodes/{}/'.format(API_BASE, self.public_node_two._id)

@pytest.mark.django_db
class TestNodeDetailViewOnlyLinks(ViewOnlyTestCase):

    def test_private_node_with_link_works_when_using_link(self):
        res_normal = self.app.get(self.private_node_one_url, auth=self.contributing_read_user.auth)
        assert res_normal.status_code == 200
        res_linked = self.app.get(self.private_node_one_url, {'view_only': self.private_node_one_private_link.key})
        assert res_linked.status_code == 200
        assert_items_equal(res_linked.json['data']['attributes']['current_user_permissions'], ['read'])

        # Remove any keys that will be different for view-only responses
        res_normal_json = res_normal.json
        res_linked_json = res_linked.json
        user_can_comment = res_normal_json['data']['attributes'].pop('current_user_can_comment')
        view_only_can_comment = res_linked_json['data']['attributes'].pop('current_user_can_comment')

        assert user_can_comment
        assert not view_only_can_comment

    def test_private_node_with_link_unauthorized_when_not_using_link(self):
        res = self.app.get(self.private_node_one_url, expect_errors=True)
        assert res.status_code == 401

    def test_private_node_with_link_anonymous_does_not_expose_contributor_id(self):
        res = self.app.get(self.private_node_one_url, {
            'view_only': self.private_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'] == ''

    def test_private_node_with_link_non_anonymous_does_expose_contributor_id(self):
        res = self.app.get(self.private_node_one_url, {
            'view_only': self.private_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in self.valid_contributors

    def test_private_node_logged_in_with_anonymous_link_does_not_expose_contributor_id(self):
        res = self.app.get(self.private_node_one_url, {
            'view_only': self.private_node_one_private_link.key,
            'embed': 'contributors',
        }, auth=self.creation_user.auth)
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in self.valid_contributors

    def test_public_node_with_link_anonymous_does_not_expose_user_id(self):
        res = self.app.get(self.public_node_one_url, {
            'view_only': self.public_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'] == ''

    def test_public_node_with_link_non_anonymous_does_expose_contributor_id(self):
        res = self.app.get(self.public_node_one_url, {
            'view_only': self.public_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in self.valid_contributors

    def test_public_node_with_link_unused_does_expose_contributor_id(self):
        res = self.app.get(self.public_node_one_url, {
            'embed': 'contributors',
        })
        assert res.status_code == 200
        contributors = res.json['data']['embeds']['contributors']['data']
        for contributor in contributors:
            assert contributor['id'].split('-')[1] in self.valid_contributors

    def test_view_only_link_does_not_grant_write_permission(self):
        payload = {
            'data': {
                'attributes': {
                    'title': 'Cannot touch this' },
                'id': self.private_node_one._id,
                'type': 'nodes',
            }
        }
        res = self.app.patch_json_api(self.private_node_one_url, payload, {
            'view_only': self.private_node_one_private_link.key,
        }, expect_errors=True)
        assert res.status_code == 401

    def test_view_only_link_from_anther_project_does_not_grant_view_permission(self):
        res = self.app.get(self.private_node_one_url, {
            'view_only': self.public_node_one_private_link.key,
        }, expect_errors=True)
        assert res.status_code == 401

    def test_private_project_logs_with_anonymous_link_does_not_expose_user_id(self):
        res = self.app.get(self.private_node_one_url+'logs/', {
            'view_only': str(self.private_node_one_anonymous_link.key),
        })
        assert res.status_code == 200
        body = res.body
        assert self.contributing_write_user._id not in body
        assert self.contributing_read_user._id not in body
        assert self.creation_user._id not in body

    def test_private_project_with_anonymous_link_does_not_expose_registrations_or_forks(self):
        res = self.app.get(self.private_node_one_url, {
            'view_only': self.private_node_one_anonymous_link.key,
        })
        assert res.status_code == 200
        relationships = res.json['data']['relationships']
        if 'embeds' in res.json['data']:
            embeds = res.json['data']['embeds']
        else:
            embeds = {}
        assert 'registrations' not in relationships
        assert 'forks' not in relationships, 'Add forks view to blacklist in hide_view_when_anonymous().'
        assert 'registrations' not in embeds
        assert 'forks' not in embeds, 'Add forks view to blacklist in hide_view_when_anonymous().'

    def test_bad_view_only_link_does_not_modify_permissions(self):
        res = self.app.get(self.private_node_one_url+'logs/', {
            'view_only': 'thisisnotarealprivatekey',
        }, expect_errors=True)
        assert res.status_code == 401
        res = self.app.get(self.private_node_one_url+'logs/', {
            'view_only': 'thisisnotarealprivatekey',
        }, auth=self.creation_user.auth)
        assert res.status_code == 200

    def test_view_only_key_in_relationships_links(self):
        res = self.app.get(self.private_node_one_url, {'view_only': self.private_node_one_private_link.key})
        assert res.status_code == 200
        res_relationships = res.json['data']['relationships']
        for key, value in res_relationships.iteritems():
            if value['links'].get('related'):
                assert self.private_node_one_private_link.key in value['links']['related']['href']
            if value['links'].get('self'):
                assert self.private_node_one_private_link.key in value['links']['self']['href']

    def test_view_only_key_in_self_and_html_links(self):
        res = self.app.get(self.private_node_one_url, {'view_only': self.private_node_one_private_link.key})
        assert res.status_code == 200
        links = res.json['data']['links']
        assert self.private_node_one_private_link.key in links['self']
        assert self.private_node_one_private_link.key in links['html']

@pytest.mark.django_db
class TestNodeListViewOnlyLinks(ViewOnlyTestCase):

    def test_private_link_does_not_show_node_in_list(self):
        res = self.app.get('/{}nodes/'.format(API_BASE), {
            'view_only': self.private_node_one_private_link.key,
        })
        assert res.status_code == 200
        nodes = res.json['data']
        node_ids = []
        for node in nodes:
            node_ids.append(node['id'])
        assert self.private_node_one._id not in node_ids

    def test_anonymous_link_does_not_show_contributor_id_in_node_list(self):
        res = self.app.get('/{}nodes/'.format(API_BASE), {
            'view_only': self.private_node_one_anonymous_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        nodes = res.json['data']
        assertions = 0
        for node in nodes:
            contributors = node['embeds']['contributors']['data']
            for contributor in contributors:
                assertions += 1
                assert contributor['id'] == ''
        assert assertions != 0

    def test_non_anonymous_link_does_show_contributor_id_in_node_list(self):
        res = self.app.get('/{}nodes/'.format(API_BASE), {
            'view_only': self.private_node_one_private_link.key,
            'embed': 'contributors',
        })
        assert res.status_code == 200
        nodes = res.json['data']
        assertions = 0
        for node in nodes:
            contributors = node['embeds']['contributors']['data']
            for contributor in contributors:
                assertions += 1
                assert contributor['id'].split('-')[1] in self.valid_contributors
        assert assertions != 0
